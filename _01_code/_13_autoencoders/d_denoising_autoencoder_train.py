import torch
from torch import nn, optim
from datetime import datetime
import os
import wandb
from pathlib import Path
import torch.nn.functional as F

BASE_PATH = str(Path(__file__).resolve().parent.parent.parent) # BASE_PATH: /Users/yhhan/git/link_dl
import sys
sys.path.append(BASE_PATH)

CURRENT_FILE_PATH = os.path.dirname(os.path.abspath(__file__))
CHECKPOINT_FILE_PATH = os.path.join(CURRENT_FILE_PATH, "checkpoints")

if not os.path.isdir(CHECKPOINT_FILE_PATH):
  os.makedirs(os.path.join(CURRENT_FILE_PATH, "checkpoints"))

from _01_code._06_fcn_best_practice.f_mnist_train_fcn import get_mnist_data
from _01_code._06_fcn_best_practice.g_mnist_test_fcn import get_mnist_test_data
from _01_code._13_autoencoders.a_arg_parser import get_parser
from _01_code._13_autoencoders.c_autoencoder_trainer import AutoencoderTrainer


def get_model(encoded_space_dim=8):
    class Encoder(nn.Module):
        def __init__(self):
            super(Encoder, self).__init__()

            ### Convolutional section
            self.encoder = nn.Sequential(
                nn.Conv2d(in_channels=1, out_channels=32, kernel_size=3, stride=1, padding=1),
                nn.BatchNorm2d(32),
                nn.ReLU(),

                nn.Conv2d(in_channels=32, out_channels=64, kernel_size=3, stride=1, padding=1),
                nn.BatchNorm2d(64),
                nn.ReLU(),

                nn.Conv2d(in_channels=64, out_channels=128, kernel_size=3, stride=1, padding=1),
                nn.BatchNorm2d(128),
                nn.ReLU(),
                nn.MaxPool2d(kernel_size=1, stride=2),

                nn.Conv2d(in_channels=128, out_channels=256, kernel_size=3, stride=1, padding=1),
                nn.BatchNorm2d(256),
                nn.ReLU(),
                nn.MaxPool2d(kernel_size=1, stride=2)
            )

        def forward(self, x):
            x = self.encoder(x)
            return x

    class Decoder(nn.Module):
        def __init__(self):
            super(Decoder, self).__init__()
            self.decoder = nn.Sequential(
                nn.ConvTranspose2d(in_channels=256, out_channels=128, kernel_size=3, stride=1, padding=1),
                nn.BatchNorm2d(128),
                nn.ReLU(),

                nn.ConvTranspose2d(in_channels=128, out_channels=64, kernel_size=2, stride=2, padding=0),
                nn.BatchNorm2d(64),
                nn.ReLU(),

                nn.ConvTranspose2d(in_channels=64, out_channels=32, kernel_size=2, stride=2, padding=0),
                nn.BatchNorm2d(32),
                nn.ReLU(),

                nn.ConvTranspose2d(in_channels=32, out_channels=1, kernel_size=3, stride=1, padding=1),
                nn.Sigmoid()
            )

        def forward(self, x):
            x = self.decoder(x)
            return x

    class Autoencoder(torch.nn.Module):
        def __init__(self):
            super(Autoencoder, self).__init__()
            self.encoder = Encoder()
            self.decoder = Decoder()

        def forward(self, x):
            x = self.encoder(x)
            x = self.decoder(x)
            return x

    autoencoder = Autoencoder()
    return autoencoder


def main(args):
    run_time_str = datetime.now().astimezone().strftime('%Y-%m-%d_%H-%M-%S')

    config = {
        'epochs': args.epochs,
        'batch_size': args.batch_size,
        'validation_intervals': args.validation_intervals,
        'learning_rate': args.learning_rate,
        'early_stop_patience': args.early_stop_patience,
        'early_stop_delta': args.early_stop_delta,
    }

    project_name = "denoising_autoencoder"
    wandb.init(
        mode="online" if args.wandb else "disabled",
        project=project_name,
        notes="denoising autoencoder",
        tags=["denoising", "autoencoder", "fashion_mnist"],
        name=run_time_str,
        config=config
    )
    print(args)
    print(wandb.config)

    train_data_loader, validation_data_loader, mnist_transforms = get_mnist_data(flatten=False)
    mnist_test_images, test_data_loader, mnist_transforms = get_mnist_test_data(flatten=False)

    device = torch.device("cuda:0" if torch.cuda.is_available() else "cpu")
    print(f"Training on device {device}.")

    model = get_model()
    model.to(device)
    wandb.watch(model)

    optimizer = optim.Adam(model.parameters(), lr=wandb.config.learning_rate)

    regression_trainer = AutoencoderTrainer(
        project_name, model, optimizer, train_data_loader, validation_data_loader, mnist_transforms,
        run_time_str, wandb, device, CHECKPOINT_FILE_PATH,
        mnist_test_images, mnist_transforms,
        denoising=False,
    )
    regression_trainer.train_loop()

    wandb.finish()


if __name__ == "__main__":
    parser = get_parser()
    args = parser.parse_args()
    main(args)

    # python _01_code/_11_lstm_and_its_application/f_crypto_currency_regression_train_lstm.py --wandb
