# convert_tgcn_to_onnx.py
import os
import torch
import argparse

# IMPORTANT: this import path must match your repo structure.
# The repo uses tgcn_model or tgcn_model.py — adapt import if the file name differs.
from code.TGCN.tgcn_model import GCN_muti_att  # change to the correct module path if needed

def load_checkpoint(ckpt_path, device='cpu'):
    ckpt = torch.load(ckpt_path, map_location=device)
    # If checkpoint is a dict('state_dict':...), change accordingly:
    if isinstance(ckpt, dict) and 'state_dict' in ckpt:
        state = ckpt['state_dict']
    else:
        state = ckpt
    return state

def main(args):
    device = torch.device('cpu') if args.onnx_only else torch.device('cuda' if torch.cuda.is_available() else 'cpu')

    # ---- Configs (edit these to match your archived/ini config or the test_tgcn settings)
    # Example values — change `num_samples` to the number used during training (from .ini in archived/)
    num_samples = args.num_samples         # temporal length used in training (frames per sample)
    input_feature = args.input_feature     # typically = num_samples * 2 in test_tgcn.py
    hidden_size = args.hidden_size
    num_classes = args.num_classes
    num_stages = args.num_stages
    dropout = args.drop_p

    # Build model (must match training construction)
    model = GCN_muti_att(input_feature=input_feature,
                         hidden_feature=hidden_size,
                         num_class=num_classes,
                         p_dropout=dropout,
                         num_stage=num_stages)

    # load weights
    state = load_checkpoint(args.checkpoint, device=device)
    # if the repo saved whole state dict directly, this loads; otherwise you may need to do state['model'] etc.
    model.load_state_dict(state)
    model.to(device)
    model.eval()

    # Create a dummy input: shape (batch_size=1, input_feature, temporal_len)
    # test_tgcn uses X slices where X.shape = (B, C, T); C == input_feature
    dummy_time = num_samples
    dummy = torch.randn(1, input_feature, dummy_time, device=device, dtype=torch.float32)

    # Export to ONNX
    dynamic_axes = {
        'input': {0: 'batch_size', 2: 'time_steps'},  # allow dynamic batch and temporal dim
        'output': {0: 'batch_size'}
    }

    onnx_path = args.onnx_output
    torch.onnx.export(
        model,
        dummy,
        onnx_path,
        export_params=True,
        opset_version=12,             # 11/12 both common; change if you need newer opset
        do_constant_folding=True,
        input_names=['input'],
        output_names=['output'],
        dynamic_axes=dynamic_axes
    )
    print(f"Exported ONNX to {onnx_path}")

if __name__ == '__main__':
    p = argparse.ArgumentParser()
    p.add_argument('--checkpoint', required=True, help='path to ckpt.pth (Torch) from archived/')
    p.add_argument('--onnx-output', default='tgcn.onnx')
    p.add_argument('--num-samples', type=int, default=64,
                   help='temporal length (frames) used in training; check the .ini in archived/')
    p.add_argument('--input-feature', type=int, default=128,
                   help='number of input channels/features (repo used num_samples * 2 in test_tgcn)')
    p.add_argument('--hidden-size', type=int, default=256)
    p.add_argument('--num-classes', type=int, default=2000)  # e.g. WLASL2000 -> 2000 classes
    p.add_argument('--num-stages', type=int, default=4)
    p.add_argument('--drop-p', type=float, default=0.5)
    p.add_argument('--onnx-only', action='store_true', help='use CPU for export if set')
    args = p.parse_args()
    main(args)
