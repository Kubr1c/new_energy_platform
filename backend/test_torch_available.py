try:
    import torch
    print('Torch is available:', torch.cuda.is_available())
    print('Torch version:', torch.__version__)
except ImportError:
    print('Torch is not available')
