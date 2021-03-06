from torch import nn, LongTensor, FloatTensor
from sklearn.utils import shuffle as skshuffle
from data.utils import batchify, rotate_point_cloud, jitter_point_cloud
from torch.autograd import Variable

class Flatten(nn.Module):
    def __init__(self):
        nn.Module.__init__(self)

    def forward(self, input):
        return input.view(input.size(0), -1)

class View2d(nn.Module):
  def __init__(self, num_channel, H, W):
    nn.Module.__init__(self)
    self.num_channel = num_channel
    self.W = W
    self.H = H

  def forward(self, x):
    result = x.view(-1, self.num_channel, self.H, self.W)
    return result

class BasePointNet(nn.Module):
    def __init__(self, n, lr, wd, cuda, device_id):
        '''
        :param dtype: 1 for (x, y, z) coordinates 2 for (x, y, z, rgb)
        :param cuda: Boolean indicating training device
        :param device_id: int indicating the CUDA device to put the model
        '''
        nn.Module.__init__(self)

        self._cuda = cuda
        self.lr = lr
        self.wd = wd

        if self._cuda:
            self.device_id = 0 if device_id is None else device_id

        self.n = n
        self.optimizer = None
        self.scheduler = None

    def forward(self, input):
        raise NotImplemented

    def loss(self, input, target):
        raise NotImplemented

    def build(self):
        if self._cuda:
            self.cuda(self.device_id)

    def fit(self, X_train, y_train, batch_size):
        self.train()
        if self. scheduler is not None:
            self.scheduler.step()
        losses = []
        X_train, y_train = skshuffle(X_train, y_train)
        X_train = rotate_point_cloud(X_train)
        X_train = jitter_point_cloud(X_train)
        X_train = X_train.reshape((-1, 1, self.n, 3))
        X_train_tensor, y_train_tensor = FloatTensor(X_train.tolist()), LongTensor(y_train.tolist())
        for x_batch, y_batch in batchify(X_train_tensor, batch_size, y_train_tensor):
            x_b, y_b = Variable(x_batch), Variable(y_batch)
            if self._cuda:
                x_b, y_b = x_b.cuda(self.device_id), y_b.cuda(self.device_id)
            self.optimizer.zero_grad()
            logits = self(x_b)
            ce = self.loss(logits, y_b)
            losses.append(ce.data[0])
            ce.backward()
            self.optimizer.step()
        return losses
    def score(self, X, y, batch_size):
        self.eval()
        X = X.reshape(-1, 1, self.n, 3)
        X_tensor, y_tensor = FloatTensor(X.tolist()), LongTensor(y.tolist())
        correct = 0.0
        for x_batch, y_batch in batchify(X_tensor, batch_size, y_tensor):
            x_b, y_b = Variable(x_batch), Variable(y_batch)
            if self._cuda:
                x_b, y_b = x_b.cuda(self.device_id), y_b.cuda(self.device_id)
            output = self(x_b)
            pred = output.data.max(1, keepdim=True)[1]
            correct += pred.eq(y_b.data.view_as(pred)).cpu().sum()
        return correct / len(y)