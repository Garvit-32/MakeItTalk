import torch
import torch.nn as nn
import torch.nn.functional as F
from torchsummary import summary
import numpy as np
from src.models.model_image_translation import ResUnetGenerator, VGGLoss
import torch_pruning as tp

model = ResUnetGenerator(input_nc=6, output_nc=3,
                         num_downs=6, use_dropout=False)
# params = sum([np.prod(p.size()) for p in model.parameters()])
# print("Number of Parameters: %.1fM" % (params/1e6))

# i = 0
# for m in model.modules():
#     # print(m)
#     if isinstance(m, nn.Conv2d):
#         print(m)
#         i += 1
# print(i)


def prune_model(model):
    model.cpu()
    DG = tp.DependencyGraph().build_dependency(model, torch.randn(10, 6, 256, 256))

    def prune_conv(conv, pruned_prob):
        weight = conv.weight.detach().cpu().numpy()
        out_channels = weight.shape[0]
        L1_norm = np.sum(np.abs(weight), axis=(1, 2, 3))
        num_pruned = int(out_channels * pruned_prob)
        # remove filters with small L1-Norm
        prune_index = np.argsort(L1_norm)[:num_pruned].tolist()
        plan = DG.get_pruning_plan(conv, tp.prune_conv, prune_index)
        plan.exec()

    block_prune_probs = []
    for i in range(90):
        if i < 40:
            block_prune_probs.append(0.1)
        if i > 40 and i < 80:
            block_prune_probs.append(0.2)
        if i > 80:
            block_prune_probs.append(0.3)
    blk_id = 0
    for m in model.modules():
        if isinstance(m, nn.Conv2d):
            prune_conv(m, block_prune_probs[blk_id])
            blk_id += 1
    return model


model = prune_model(model).to('cuda')

params = sum([np.prod(p.size()) for p in model.parameters()])
print("Number of Parameters: %.1fM" % (params/1e6))