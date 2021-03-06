import torch
from torchvision import datasets, transforms
import random
import torch
from torchvision.transforms import ToTensor
from torch.utils.data import DataLoader, Dataset, Subset
from torchvision.models import resnet50
import copy
from torch.nn import functional as F 
from torch.autograd import Variable
import torch.nn as nn
from torch import optim
import numpy as np
import matplotlib.pyplot as plt
import pylab

from sklearn.datasets import fetch_openml
from sklearn.model_selection import train_test_split
 
batch_size = 56000
device = 'cuda'
CLASS_SIZE = 10

class MNISTDataset(Dataset):
    
    def __init__(self, transform=None):
        self.mnist = fetch_openml('mnist_784', version=1,)
        self.data = self.mnist.data.reshape(-1, 28, 28).astype('uint8')
        self.target = self.mnist.target.astype(int)
        self.indices = range(len(self))
        self.transform = transform
        
    def __len__(self):
        return len(self.data)
    
    def __getitem__(self, idx):
        idx2 = random.choice(self.indices)
        data1 = self.data[idx]
        #data2 = self.data[idx2] 
        target1 = torch.from_numpy(np.array(self.target[idx])) #torch.from_numpy()でTensorに変換
        if self.transform:
            data1 = self.transform(data1)
        
        #sample = data1
        return data1, target1


class VAE(nn.Module):
    def __init__(self, z_dim):
        super(VAE, self).__init__()
        self.dense_enc1 = nn.Linear(28*28 + CLASS_SIZE, 200)
        self.dense_enc2 = nn.Linear(200, 100)
        self.dense_encmean = nn.Linear(100, z_dim)
        self.dense_encvar = nn.Linear(100, z_dim)
        self.dense_dec1 = nn.Linear(z_dim, 100)
        self.dense_dec2 = nn.Linear(100, 200)
        self.dense_dec3 = nn.Linear(200, 28*28)

    def _encoder(self, x):
        x = F.relu(self.dense_enc1(x))
        x = F.relu(self.dense_enc2(x))
        mean = self.dense_encmean(x)
        var = self.dense_encvar(x)
        return mean, var

    def _sample_z(self, mean, var): #普通にやると誤差逆伝搬ができないのでReparameterization Trickを活用
        epsilon = torch.randn(mean.shape).to(device)
        print(epsilon)
        print(mean.shape)
        return mean + epsilon * torch.exp(0.5*var)
        # イメージとしては正規分布の中からランダムにデータを取り出している
        #入力に対して潜在空間上で類似したデータを復元できるように学習, 潜在変数を変化させると類似したデータを生成
        #Autoencoderは決定論的入力と同じものを復元しようとする

    def _decoder(self,z):
        x = F.relu(self.dense_dec1(z))
        x = F.relu(self.dense_dec2(x))
        x = F.sigmoid(self.dense_dec3(x))
        return x

    def forward(self, x):
        mean, var = self._encoder(x)
        z = self._sample_z(mean, var)
        x = self._decoder(z)
        return x, mean, var, z

    def to_onehot(self, label): #ラベルをone-hotに変換, labelはリスト[0, 1, 5, 6, 8, 9]など
        return torch.eye(CLASS_SIZE, device=device, dtype=torch.float32)[label]

    def loss(self, x, y, mean, var): #lossは交差エントロピーを採用している, MSEの事例もある
        KL = -0.5 * torch.sum(1 + var - mean.pow(2) - var.exp())
        reconstruction = F.binary_cross_entropy(y, x.view(-1, 784), size_average=False)
        return KL + reconstruction


def vis_data(model, train_loader):
    #concat_label = np.array([0]) #batchごとに結合するために, 定義用のものを用意
    #concat_data = torch.zeros([1, 784], dtype=torch.float64).to(device)
    for data, label in train_loader:
        label_one_hot = model.to_onehot(label)
        data = data.view(data.shape[0], -1) 
        in_ = torch.empty((data.shape[0], 28*28 + CLASS_SIZE), device = device)
        in_[:, :28*28] = data
        in_[:, 28*28:] = label_one_hot
        data = data.to(device)
        label = label.detach().numpy()
        break
    
    x_recon, mean, var, z= model(in_) 
    z = Variable(z, volatile=True).cpu().numpy()
    x_recon = Variable(x_recon, volatile=True).cpu().numpy()
    data = Variable(data, volatile=True).cpu().numpy() #recon
    #z = Variable(mean, volatile=True).cpu().numpy() #batch_size問題のデバッグ
    plt.figure(figsize=(10, 10))
    plt.scatter(z[:, 0], z[:, 1], marker='.', c=label, cmap=pylab.cm.jet)
    sum = 0
    for i in range(10):
        tmp  = np.where(label == i)
        print(np.var(z[tmp]))
        sum += np.var(z[tmp])
    sum /= 10
    print("Ave var: " + str(sum))
    quit()
    plt.colorbar()
    plt.grid()
    plt.title('oza_CVAE_2dimention')
    plt.savefig('senzai0629_2.png')


def load_model(train_loader):
    #global device
    #device = device("cuda" if cuda.is_available() else "cpu")
    z_dim = 2
    model = VAE(z_dim).to(device)
    model.load_state_dict(torch.load("/home/oza/pre-experiment/CVAE/mnist_param/mnist_test1_2.pth", map_location=device))
    vis_data(model, train_loader)

def main():
    train_data = MNISTDataset(transform=ToTensor())
    n_samples = len(train_data) # n_samples is 60000
    train_size = int(len(train_data) * 0.8) # train_size is 48000
    val_size = n_samples - train_size # val_size is 48000
 
    # shuffleしてから分割してくれる.
    train_dataset, val_dataset = torch.utils.data.random_split(train_data, [train_size, val_size])

    train_loader = DataLoader(val_dataset, batch_size = batch_size, shuffle=True)
    load_model(train_loader)
    
if __name__ == "__main__":
    main()  

