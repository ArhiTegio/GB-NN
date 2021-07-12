import numpy as np
from threading import Thread
import sys
import os


def load_dataset():
    # We first define a download function, supporting both Python 2 and 3.
    if sys.version_info[0] == 2:
        from urllib import urlretrieve
    else:
        from urllib.request import urlretrieve

    def download(filename, source='http://yann.lecun.com/exdb/mnist/'):
        print("Downloading %s" % filename)
        urlretrieve(source + filename, filename)

    # We then define functions for loading MNIST images and labels.
    # For convenience, they also download the requested files if needed.
    import gzip

    def load_mnist_images(filename):
        if not os.path.exists(filename):
            download(filename)
        # Read the inputs in Yann LeCun's binary format.
        with gzip.open(filename, 'rb') as f:
            data = np.frombuffer(f.read(), np.uint8, offset=16)
        # The inputs are vectors now, we reshape them to monochrome 2D images,
        # following the shape convention: (examples, channels, rows, columns)
        data = data.reshape(-1, 1, 28, 28)
        # The inputs come as bytes, we convert them to float32 in range [0,1].
        # (Actually to range [0, 255/256], for compatibility to the version
        # provided at http://deeplearning.net/data/mnist/mnist.pkl.gz.)
        return data / np.float32(256)

    def load_mnist_labels(filename):
        if not os.path.exists(filename):
            download(filename)
        # Read the labels in Yann LeCun's binary format.
        with gzip.open(filename, 'rb') as f:
            data = np.frombuffer(f.read(), np.uint8, offset=8)
        # The labels are vectors of integers now, that's exactly what we want.
        return data

    # We can now download and read the training and test set images and labels.
    X_train = load_mnist_images('train-images-idx3-ubyte.gz')
    y_train = load_mnist_labels('train-labels-idx1-ubyte.gz')
    X_test = load_mnist_images('t10k-images-idx3-ubyte.gz')
    y_test = load_mnist_labels('t10k-labels-idx1-ubyte.gz')

    return (X_train, y_train),  (X_test, y_test)


   
(X_train, y_train), (X_test, y_test) = load_dataset()
X_train = X_train.reshape(X_train.shape[0], -1, 1)
X_test = X_test.reshape(X_test.shape[0], -1, 1)
X_train = X_train.astype('float32')
X_test = X_test.astype('float32')
X_train -= 0.5
X_test -= 0.5
X_train *= 2
X_test *= 2

class batch_thread():
  def __init__(self, result, batch_size_):
    self.result = result
    self.batch_size_=batch_size_
    self.indices = np.arange(len(y_train))
    np.random.shuffle(self.indices)
    self.idx=0
  def __call__(self): 
    batch_data_  = np.zeros((self.batch_size_, X_train.shape[1], X_train.shape[2]), dtype=np.float32)
    batch_label_ = np.zeros((self.batch_size_), dtype=np.int32)
    for i in range(self.batch_size_):
      batch_data_[i,:,:]=X_train[self.indices[self.idx],:,:]
      batch_label_[i]=y_train[self.indices[self.idx]]
      self.idx+=1
      if self.idx==len(self.indices):
        self.idx=0
        np.random.shuffle(self.indices)
         
    self.result['data']=batch_data_
    self.result['label']=batch_label_ 


class DataHandler(object):

  def __init__(self, batch_size):
    self.batch_size_ = batch_size    # batch size            

    self.batch_data_  = np.zeros((self.batch_size_, 3, 32, 32), dtype=np.float32)
    self.batch_label_ = np.zeros((self.batch_size_), dtype=np.int32)
    
    self.thread_result = {}
    self.thread = None
    self.batch_advancer =batch_thread(self.thread_result,self.batch_size_)
    
    
    self.dispatch_worker()
    self.join_worker()


  def get_batch(self):
    #self.batch_data_  = np.zeros((self.batch_size_, 3, self.seq_length_, 112, 112), dtype=np.float32)
    if self.thread is not None:
      self.join_worker() 
      
    self.batch_data_=self.thread_result['data']
    self.batch_label_=self.thread_result['label']
    
    self.dispatch_worker()
    return self.batch_data_, self.batch_label_


  def dispatch_worker(self):
    assert self.thread is None
    self.thread = Thread(target=self.batch_advancer)
    self.thread.start()

  def join_worker(self):
    assert self.thread is not None
    self.thread.join()
    self.thread = None

  def GetDatasetSize(self):
    return len(y_train)//(2*self.batch_size_)




class testbatch_thread():
  def __init__(self, result, batch_size_):
    self.result = result
    self.batch_size_=batch_size_
    self.indices = np.arange(len(y_test))
    np.random.shuffle(self.indices)
    self.idx=0
  def __call__(self):    
    batch_data_  = np.zeros((self.batch_size_, X_test.shape[1], X_test.shape[2]), dtype=np.float32)
    batch_label_ = np.zeros((self.batch_size_), dtype=np.int32)
    if self.idx+self.batch_size_>len(y_test):
      batch_data_[:len(y_test)-self.idx]=X_test[self.indices[self.idx:len(y_test)],:,:]
      batch_label_[:len(y_test)-self.idx]=y_test[self.indices[self.idx:len(y_test)]]
      needed=self.batch_size_-(len(y_test)-self.idx)
      batch_data_[len(y_test)-self.idx:]=X_test[self.indices[0:needed],:,:]
      batch_label_[len(y_test)-self.idx:]=y_test[self.indices[0:needed]]
      self.idx=needed
    else:
      batch_data_=X_test[self.indices[self.idx:self.idx+self.batch_size_],:,:]
      batch_label_=y_test[self.indices[self.idx:self.idx+self.batch_size_]]
      self.idx+=self.batch_size_
            
    self.result['data']=batch_data_
    self.result['label']=batch_label_
    
    if self.idx==len(y_test):
        self.idx=0


class testDataHandler(object):

  def __init__(self, batch_size):
    self.batch_size_ = batch_size    # batch size            

    self.batch_data_  = np.zeros((self.batch_size_, X_test.shape[1], X_test.shape[2]), dtype=np.float32)
    self.batch_label_ = np.zeros((self.batch_size_), dtype=np.int32)
    
    self.thread_result = {}
    self.thread = None
    self.batch_advancer =testbatch_thread(self.thread_result,self.batch_size_)
    
    
    self.dispatch_worker()
    self.join_worker()


  def get_batch(self):
    #self.batch_data_  = np.zeros((self.batch_size_, 3, self.seq_length_, 112, 112), dtype=np.float32)
    if self.thread is not None:
      self.join_worker() 
      
    self.batch_data_=self.thread_result['data']
    self.batch_label_=self.thread_result['label']
    
    self.dispatch_worker()
    return self.batch_data_, self.batch_label_


  def dispatch_worker(self):
    assert self.thread is None
    self.thread = Thread(target=self.batch_advancer)
    self.thread.start()

  def join_worker(self):
    assert self.thread is not None
    self.thread.join()
    self.thread = None
  def GetDatasetSize(self):
    return len(y_test)//self.batch_size_
  
  
  
  
  
  
  
  
  
class finaltestbatch_thread():
  def __init__(self, result, batch_size_):
    self.result = result
    self.batch_size_=batch_size_
    self.idx=0
  def __call__(self):    
    temp_data_  = np.zeros((self.batch_size_*2, 3, 32, 32), dtype=np.float32)
    temp_label_ = np.zeros((self.batch_size_*2), dtype=np.int32)
    
    temp_data_[::2,:,:,:]=X_test[self.idx:self.idx+self.batch_size_,:,:,:]
    temp_label_[::2]=y_test[self.idx:self.idx+self.batch_size_]
    
    temp_data_[1::2,:,:,:]=X_test[self.idx:self.idx+self.batch_size_,:,:,::-1]
    temp_label_[1::2]=y_test[self.idx:self.idx+self.batch_size_]
          
    self.result['data']=temp_data_
    self.result['label']=temp_label_
    self.idx+=self.batch_size_
    if self.idx==len(y_test):
        self.idx=0


class finaltestDataHandler(object):

  def __init__(self, batch_size):
    self.batch_size_ = batch_size    # batch size            

    self.batch_data_  = np.zeros((self.batch_size_*2, 3, 32, 32), dtype=np.float32)
    self.batch_label_ = np.zeros((self.batch_size_*2), dtype=np.int32)
    
    self.thread_result = {}
    self.thread = None
    self.batch_advancer =finaltestbatch_thread(self.thread_result,self.batch_size_)
    
    
    self.dispatch_worker()
    self.join_worker()


  def get_batch(self):
    #self.batch_data_  = np.zeros((self.batch_size_, 3, self.seq_length_, 112, 112), dtype=np.float32)
    if self.thread is not None:
      self.join_worker() 
      
    self.batch_data_=self.thread_result['data']
    self.batch_label_=self.thread_result['label']
    
    self.dispatch_worker()
    return self.batch_data_, self.batch_label_


  def dispatch_worker(self):
    assert self.thread is None
    self.thread = Thread(target=self.batch_advancer)
    self.thread.start()

  def join_worker(self):
    assert self.thread is not None
    self.thread.join()
    self.thread = None
  def GetDatasetSize(self):
    return len(y_test)//self.batch_size_
