import torch as t
from torch import nn
import ipdb
import torch.nn.functional as F
from .transformer import TabularEmbedding


class Conv1DLayers(nn.Module):
    def __init__(self, layers, in_channels, out_channels, dropout=0.2) -> None:
        super().__init__()

        self.layers = nn.Sequential()
        for i in range(layers):
            self.layers.append(
                Conv1DBlock(
                    in_channels,
                    out_channels,
                    kernel_size=3,
                    stride=1,
                    padding=1,
                    dilation=1,
                    groups=1,
                    bias=True,
                    drouput=dropout,
                    residual=False,
                )
            )
            in_channels = out_channels

    def forward(self, x):
        x = self.layers(x)
        return x


class Conv1DBlock(nn.Module):
    def __init__(
        self,
        in_channels,
        out_channels,
        kernel_size,
        stride=1,
        padding=0,
        dilation=1,
        groups=1,
        bias=True,
        drouput=0.5,
        residual=False,
    ):
        super().__init__()
        self.conv1d = nn.Conv1d(
            in_channels,
            out_channels,
            kernel_size,
            stride,
            padding,
            dilation,
            groups,
            bias,
        )
        self.bn = nn.BatchNorm1d(out_channels)
        self.relu = nn.ReLU()
        self.do = nn.Dropout(drouput)
        self.init_weights()

    def forward(self, x):

        x = self.conv1d(x)
        x = self.bn(x)
        x = self.relu(x)
        x = self.do(x)
        return x

    def init_weights(self):

        # init weights of conv1d

        nn.init.kaiming_normal_(self.conv1d.weight, mode="fan_out", nonlinearity="relu")
        nn.init.constant_(self.conv1d.bias, 0)

        # init weights of bn

        nn.init.constant_(self.bn.weight, 1)
        nn.init.constant_(self.bn.bias, 0)


# Conv1d Classifier
class Conv1dClassifier(nn.Module):
    def __init__(self, in_channels=248, num_class=4):
        super(Conv1dClassifier, self).__init__()

        self.conv1 = Conv1DBlock(
            in_channels, 256, kernel_size=self.kernel_size, stride=1, padding=1
        )
        self.conv2 = Conv1DBlock(
            256, 256, kernel_size=self.kernel_size, stride=1, padding=1
        )
        self.conv3 = Conv1DBlock(
            256, 256, kernel_size=self.kernel_size, stride=1, padding=1
        )
        self.conv4 = Conv1DBlock(
            256, 256, kernel_size=self.kernel_size, stride=1, padding=1, drouput=0
        )
        # spacial attention
        self.classifier = nn.Linear(256, num_class)
        self.noise_layer = GaussianNoise(0.1, True)

    def forward(self, x):
        # ipdb.set_trace()
        x = x.squeeze(1)
        x = self.noise_layer(x)
        x = self.conv1(x)
        x = self.conv2(x)
        x = self.conv3(x)
        x = self.conv4(x)
        # ipdb.set_trace()
        x = x.max(dim=2)[0]
        x = x.view(x.size(0), -1)
        x = self.classifier(x)
        return F.softmax(x, dim=1)


# Conv1d Classifier
class FitConv1dClassifier(nn.Module):
    def __init__(self, in_channels=248, num_class=4):
        super(FitConv1dClassifier, self).__init__()

        self.dim = 64
        self.kernel_size = 4
        self.droupout = 0.01
        # 248x195
        self.conv1 = Conv1DBlock(
            in_channels,
            self.dim,
            kernel_size=self.kernel_size,
            stride=1,
            padding=1,
            drouput=0,
        )
        # 256x195
        self.conv2 = Conv1DBlock(
            self.dim,
            self.dim,
            kernel_size=self.kernel_size,
            stride=1,
            padding=1,
            drouput=0.05,
        )
        # 256x98
        self.conv3 = Conv1DBlock(
            self.dim,
            self.dim,
            kernel_size=self.kernel_size,
            stride=1,
            padding=1,
            drouput=self.droupout,
        )
        # 256x49
        # self.conv4 = Conv1DBlock(self.dim, self.dim, kernel_size=self.kernel_size, stride=1, padding=1, drouput=0.1)
        # spacial attention
        self.classifier = nn.Linear(self.dim, num_class)
        # self.bclassifier = nn.Sequential(
        #     nn.Linear(34368, 2000), nn.ReLU(), nn.Linear(2000, num_class)
        # )
        self.noise_layer = GaussianNoise(0.01, False)

    def forward(self, x):
        # ipdb.set_trace()
        x = x.squeeze(1)
        x = self.noise_layer(x)
        x = self.conv1(x)
        x = self.conv2(x)
        x = self.conv3(x)
        # x = self.conv4(x)
        # ipdb.set_trace()
        x = x.max(dim=2)[0]
        x = x.view(x.size(0), -1)
        x = self.classifier(x)
        return F.softmax(x, dim=1)


class GaussianNoise(nn.Module):
    def __init__(self, stddev, minmax=False):
        super().__init__()
        self.stddev = stddev
        self.minmax = minmax

    def forward(self, x):
        if self.training:
            if self.minmax:
                range = x.max() - x.min()
                noise = t.randn(x.shape).to(x.device) * range * self.stddev
            else:
                noise = t.randn(x.shape).to(x.device) * self.stddev
            return x + noise
        else:
            return x


class AmexConv1DClassifier(nn.Module):
    def __init__(
        self,
        params,
        in_channels=13,
    ):
        super().__init__()
        self.params = params

        # Dim = 64 + 188 = 242
        self.layers = nn.Sequential(
            Conv1DBlock(13, 64, 3, stride=1, padding=1),
            Conv1DBlock(64, 128, 3, stride=1, padding=1),
            Conv1DBlock(128, 256, 3, stride=1, padding=1),
            nn.MaxPool1d(2, 2),  # 256x 126
            Conv1DBlock(256, 512, 3, stride=1, padding=1),
            nn.MaxPool1d(2, 2),  # 512 x 62
            Conv1DBlock(512, 1024, 3, stride=1, padding=1),
            nn.MaxPool1d(2, 2),  # 1024 x 31
            Conv1DBlock(1024, 512, 3, stride=1, padding=1),
            Conv1DBlock(512, 256, 3, stride=1, padding=1),
            Conv1DBlock(256, 128, 3, stride=1, padding=1),
        )

        self.classifier = nn.Linear(128, 1)
        self.act = nn.Sigmoid()
        self.noise_layer = GaussianNoise(0.1)

    def forward(self, x):
        x = self.noise_layer(x)
        x = x.squeeze(1)
        if self.params.hparams.noise_dim > 0:
            rand_noise = t.randn(*x.shape[:2], self.params.hparams.noise_dim).to(
                x.device
            )
            x = t.cat([x, rand_noise], dim=2)

        x = self.layers(x)
        x = x.max(dim=2)[0]
        x = x.view(x.size(0), -1)
        x = self.classifier(x)
        x = self.act(x)
        return x


class DoubleConv1DClassifier(nn.Module):
    def __init__(
        self,
        params,
        in_channels=13,
    ):
        super().__init__()
        self.params = params

        # Dim = 64 + 188 = 242
        self.layers = nn.Sequential(
            Conv1DBlock(13, 64, 3, stride=1, padding=1),
            Conv1DBlock(64, 128, 3, stride=1, padding=1),
            Conv1DBlock(128, 256, 3, stride=1, padding=1),
            nn.MaxPool1d(2, 2),  # 256x 126
            Conv1DBlock(256, 512, 3, stride=1, padding=1),
            nn.MaxPool1d(2, 2),  # 512 x 62
            Conv1DBlock(512, 1024, 3, stride=1, padding=1),
            nn.MaxPool1d(2, 2),  # 1024 x 31
            Conv1DBlock(1024, 512, 3, stride=1, padding=1),
            Conv1DBlock(512, 256, 3, stride=1, padding=1),
            # Conv1DBlock(256, 128, 3, stride=1, padding=1),
        )

        # Dim -> 242 x 13
        self.transpose_layers = nn.Sequential(
            Conv1DBlock(
                157 * self.params.hparams.feature_embed_dim, 256, 3, stride=1, padding=1
            ),
            Conv1DBlock(256, 512, 3, stride=1, padding=1),
            Conv1DBlock(512, 1024, 3, stride=1, padding=1),
            nn.MaxPool1d(2, 2),  # 1024 x 6
            Conv1DBlock(1024, 512, 3, stride=1, padding=1),
            Conv1DBlock(512, 256, 3, stride=1, padding=1),
            # Conv1DBlock(256, 128, 3, stride=1, padding=1),
        )

        self.classifier = nn.Linear(256, 1)
        self.embedding = TabularEmbedding(params=params)
        self.time_embeddig = nn.Embedding(
            13, 157 * self.params.hparams.feature_embed_dim
        )
        self.act = nn.Sigmoid()

    def forward(self, x):

        # randomly set 20% of data to nan
        if self.training:
            rand = t.rand_like(x, device=x.device)
            max_prob = self.params.hparams.nan_prob
            min_prob = self.params.hparams.min_nan_prob
            # nan_prob is between min_nan_prob and max_nan_prob
            nan_prob = min_prob + (max_prob - min_prob) * t.rand(1, device=x.device)[0]
            nan_mask = rand < nan_prob
            x[nan_mask] = t.nan

        x = self.embedding(x)
        time_embed = self.time_embeddig(t.arange(0, 13, device=x.device))

        time_embed = time_embed.repeat(x.shape[0], 1, 1)
        x = time_embed + x
        x_t = x.permute(0, 2, 1)

        x = self.layers(x)
        x = x.max(dim=2)[0]
        x = x.view(x.size(0), -1)

        x_t = self.transpose_layers(x_t)
        x_t = x_t.max(dim=2)[0]
        x_t = x_t.view(x_t.size(0), -1)

        x = x + x_t

        x = self.classifier(x)
        # x = self.act(x)
        return x


# FAT Conv1d Classifier
class FATConv1dClassifier(nn.Module):
    def __init__(
        self,
        params,
        in_channels=13,
        hidden_channel=512,
        num_layers=6,
        dropout=0.3,
        num_class=1,
    ):
        super(FATConv1dClassifier, self).__init__()

        self.params = params

        try:
            hidden_channel = self.params.hparams.hidden_dim
            num_layers = self.params.hparams.num_layers
            dropout = self.params.hparams.dropout
        except:
            pass

        for i in range(num_layers):

            setattr(
                self,
                f"conv{i}",
                Conv1DBlock(
                    in_channels,
                    hidden_channel,
                    kernel_size=3,
                    stride=1,
                    padding=1,
                    drouput=dropout,
                ),
            )
            in_channels = hidden_channel

        self.classifier = nn.Linear(hidden_channel, num_class)
        self.num_layers = num_layers
        self.noise_layer = GaussianNoise(0.05, False)

    def forward(self, x):
        # ipdb.set_trace()
        x = self.noise_layer(x)
        x = x.squeeze(1)
        if self.params.hparams.noise_dim > 0:
            rand_noise = t.randn(*x.shape[:2], self.params.hparams.noise_dim).to(
                x.device
            )
            x = t.cat([x, rand_noise], dim=2)
        for i in range(self.num_layers):
            x = getattr(self, f"conv{i}")(x)

        x = x.max(dim=2)[0]
        x = x.view(x.size(0), -1)
        x = self.classifier(x)
        return F.sigmoid(x)


# Conv1d Classifier
class Res1D(nn.Module):
    def __init__(self, in_channels=248, num_class=4):
        super(Res1D, self).__init__()

        self.dim = 256
        self.kernel_size = 1
        self.droupout = 0.01
        # 248x195
        self.conv1 = Conv1DResidual(
            in_channels,
            self.dim,
            kernel_size=self.kernel_size,
            stride=1,
            padding=1,
            drouput=self.droupout,
        )
        # 256x195
        self.conv2 = Conv1DResidual(
            self.dim,
            self.dim,
            kernel_size=self.kernel_size,
            stride=1,
            padding=1,
            drouput=self.droupout,
        )
        # 256x98
        self.conv3 = Conv1DResidual(
            self.dim,
            self.dim,
            kernel_size=self.kernel_size,
            stride=1,
            padding=1,
            drouput=self.droupout,
        )
        # 256x49
        # self.conv4 = Conv1DBlock(self.dim, self.dim, kernel_size=self.kernel_size, stride=1, padding=1, drouput=0.1)
        # spacial attention
        self.classifier = nn.Linear(self.dim, num_class)
        # self.bclassifier = nn.Sequential(
        #     nn.Linear(34368, 2000), nn.ReLU(), nn.Linear(2000, num_class)
        # )
        self.noise_layer = GaussianNoise(2, False)

    def forward(self, x):
        # ipdb.set_trace()
        x = x.squeeze(1)
        # ipdb.set_trace()
        x = self.noise_layer(x)
        x = self.conv1(x)
        x = self.conv2(x)
        x = self.conv3(x)
        # x = self.conv4(x)
        # ipdb.set_trace()
        x = x.max(dim=2)[0]
        x = x.view(x.size(0), -1)
        x = self.classifier(x)
        return F.softmax(x, dim=1)


class Conv1DResidual(nn.Module):
    def __init__(
        self, in_channels, out_channels, kernel_size=16, stride=1, padding=1, drouput=0
    ):
        super(Conv1DResidual, self).__init__()
        self.conv1 = nn.Conv1d(in_channels, out_channels, 1, stride, padding)
        self.bn1 = nn.BatchNorm1d(out_channels)
        self.relu = nn.ReLU()
        self.conv2 = nn.Conv1d(out_channels, out_channels, 16, stride, padding)
        self.bn2 = nn.BatchNorm1d(out_channels)
        self.drouput = drouput
        self.dropout = nn.Dropout(self.drouput)
        self.do = nn.Dropout(drouput)

    def forward(self, x):
        residual = x
        re_res = self.do(x)
        x = self.conv1(x)
        # residual = self.do(x)
        x = self.conv2(x)
        # ipdb.set_trace()
        if residual.shape == x.shape:
            x = x + residual
        # if re_res.shape == x.shape:
        #     x = x + re_res

        x = self.bn1(x)
        x = self.relu(x)
        x = self.do(x)
        return x
