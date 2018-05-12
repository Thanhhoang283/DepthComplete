from __future__ import print_function, absolute_import
import argparse
import os,sys
import shutil
import time
import math
import os.path as osp
import numpy as np
from PIL import Image

fileDir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, fileDir)

import torch
import torch.nn as nn
import torch.nn.parallel
import torch.nn.functional as F
import torch.backends.cudnn as cudnn
import torch.optim
import torch.utils.data
import torchvision.transforms as T
import torchvision.transforms.functional as TF
from torch.optim import lr_scheduler

import models
from models.SparseConvNet import *
import datasets
from datasets.depth_loader import DepthDataset, depth_transform
from util.utils import AverageMeter, Logger, save_checkpoint, Evaluate
from util.criterion import init_criterion, get_criterions

parser = argparse.ArgumentParser(description='PyTorch Depth Completion Testing')
parser.add_argument('resume', type=str, metavar='PATH',
                    help='path to latest checkpoint (default: none)')
parser.add_argument('--dataset', default='kitti', choices=datasets.get_names(),
                    help='name of dataset')
parser.add_argument('--data-root', default='./data', help='root path to datasets')
parser.add_argument('--save-root', default='./checkpoints', help='root path to datasets')
parser.add_argument('--arch', '-a', metavar='ARCH', default='sparseconv',
                    choices=models.get_names(),
                    help='model architecture: ' +
                        ' | '.join(models.get_names()) +
                        ' (default: sparseconv)')
parser.add_argument('--tag', default='test', help='tag in save path')
parser.add_argument('--height', type=int, default=352,
                    help="height of an image (default: 256)")
parser.add_argument('--width', type=int, default=1216,
                    help="width of an image (default: 128)")
parser.add_argument('-j', '--workers', default=4, type=int, metavar='N',
                    help='number of data loading workers (default: 4)')
parser.add_argument('-b', '--batch-size', default=64, type=int,
                    metavar='N', help='mini-batch size (default: 64)')
parser.add_argument('--print-freq', '-p', default=10, type=int,
                    metavar='N', help='print frequency (default: 10)')
parser.add_argument('--gpu-ids', default='0', type=str, help='gpu device ids for CUDA_VISIBLE_DEVICES')


def main():
    global args
    args = parser.parse_args()

    os.environ['CUDA_VISIBLE_DEVICES'] = args.gpu_ids
    cudnn.benchmark = True

    args.save_root = osp.join(args.save_root, args.dataset, args.tag)
    print("==========\nArgs:{}\n==========".format(args))

    # create model
    print("=> creating model '{}'".format(args.arch))
    model = models.init_model(name=args.arch)
    print("Model size: {:.5f}M".format(sum(p.numel() for p in model.parameters())/1000000.0))
    # optionally resume from a checkpoint
    if os.path.isfile(args.resume):
        print("=> loading checkpoint '{}'".format(args.resume))
        checkpoint = torch.load(args.resume)
        model.load_state_dict(checkpoint['state_dict'])
    else:
        print("=> no checkpoint found at '{}'".format(args.resume))
        return

    model = torch.nn.DataParallel(model).cuda()

    print("Initializing dataset {}".format(args.dataset))
    dataset = datasets.init_dataset(args.dataset, root=osp.join(args.data_root,args.dataset))

    print("===> Start testing")
    with torch.no_grad():
        for img in dataset.valset_select:
            raw_path = osp.join(args.data_root,args.dataset,img)
            raw_pil = Image.open(raw_path)
            raw = depth_transform(raw_pil)
            raw = TF.to_tensor(raw).float()
            input = torch.unsqueeze(raw,0).cuda()
            output = model(input) * 256
            pil_img = output[0].cpu().int16().ToPILImage()
            pil_img.save(osp.join(args.save_root, img))
            print(img+' finish.')

if __name__ == '__main__':
    main()