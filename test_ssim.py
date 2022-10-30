# Dependencies:
#   pip install scikit-image numpy SSIM-PIL pyssim pyopencl pytorch
import os
from concurrent.futures import ProcessPoolExecutor, ThreadPoolExecutor, as_completed
from contextlib import contextmanager
from itertools import combinations
from multiprocessing import freeze_support
from os.path import basename
from time import time

import numpy as np
import tensorflow as tf
from PIL import Image
from skimage.metrics import structural_similarity as ssim
from ssim import SSIM, compute_ssim
from SSIM_PIL import compare_ssim

os.environ['PYOPENCL_COMPILER_OUTPUT'] = '1'

PATH_1 = 'assets/demo_images/78513963.jpg'
PATH_2 = 'assets/demo_images/78513963_500px.jpg'
PATH_3 = 'assets/demo_images/78513963_1000px_darkened.jpg'
PATH_4 = 'assets/demo_images/78513963_1000px_low_contrast.jpg'
# PATH_5 = 'assets/demo_images/78513963_1000px_noise.jpg'  # Almost never matches
PATH_6 = 'assets/demo_images/48849031626_af2065ab64_k.jpg'
IMG_COMBINATIONS = list(combinations([PATH_1, PATH_2, PATH_3, PATH_4, PATH_6], 2))
IMG_COMBINATIONS += [(PATH_1, PATH_1)]


@contextmanager
def timeit(n_iterations=None):
    start_time = time()
    yield
    elapsed = time() - start_time
    avg = f' (avg: {elapsed/10:.3f}s)' if n_iterations else ''
    print(f'Elapsed: {elapsed:.2f}s{avg}')


def test_ssim_func(ssim_func, log_results=True, **kwargs):
    print(f'\nTesting {ssim_func.__name__}')
    print('-' * 30)
    with timeit(n_iterations=len(IMG_COMBINATIONS)):
        for path_1, path_2 in IMG_COMBINATIONS:
            value = ssim_func(path_1, path_2, **kwargs)
            if log_results:
                print(f'{basename(path_1)} | {basename(path_2)}:\t{value:.2f}')


def test_ssim_func__parallel(
    ssim_func,
    log_results=True,
    executor_cls=ProcessPoolExecutor,
    **kwargs,
):
    exec_type = 'multiprocess' if executor_cls == ProcessPoolExecutor else 'multithreaded'
    print(f'\nTesting {ssim_func.__name__} ({exec_type})\n' + ('-' * 30))

    with timeit(n_iterations=len(IMG_COMBINATIONS)), executor_cls() as executor:
        futures_to_paths = {}
        for path_1, path_2 in IMG_COMBINATIONS:
            future = executor.submit(ssim_func, path_1, path_2, **kwargs)
            futures_to_paths[future] = (path_1, path_2)

        for future in as_completed(futures_to_paths.keys()):
            path_1, path_2 = futures_to_paths[future]
            value = future.result()
            if log_results:
                print(f'{basename(path_1)} | {basename(path_2)}:\t{value:.2f}')


def _resize_equal(path_1, path_2):
    """Resize the larger of two images to match the resolution of the smaller one"""
    img_1 = Image.open(path_1).convert('L')
    img_2 = Image.open(path_2).convert('L')

    if img_1.size == img_2.size:
        return img_1, img_2
    elif img_1.height > img_2.height:
        max_img, min_img = img_1, img_2
    else:
        max_img, min_img = img_2, img_1

    max_img = max_img.resize((min_img.width, min_img.height), Image.Resampling.LANCZOS)
    return max_img, min_img


def test_ssim_pil(path_1, path_2, GPU=False):
    img_1, img_2 = _resize_equal(path_1, path_2)
    return compare_ssim(img_1, img_2, GPU=GPU)


def test_ssim_pil_gpu(*args):
    return test_ssim_pil(*args, GPU=True)


def test_pyssim(path_1, path_2):
    return compute_ssim(path_1, path_2)


def test_pyssim_cw(path_1, path_2):
    return SSIM(path_1).cw_ssim_value(path_2)


def test_scikit_image(path_1, path_2):
    pil_img_1, pil_img_2 = _resize_equal(path_1, path_2)
    img_1, img_2 = np.asarray(pil_img_1), np.asarray(pil_img_2)
    return ssim(img_1, img_2, gaussian_weights=True)


# Tensorflow: Compute SSIM over tf.uint8 Tensors
def test_tf_uint8(path_1, path_2):
    img_1, img_2 = _get_tf_img_arrays(path_1, path_2)

    value = tf.image.ssim(
        img_1, img_2, max_val=255, filter_size=11, filter_sigma=1.5, k1=0.01, k2=0.03
    )
    return float(value)


# Tensorflow: Compute SSIM over tf.float32 Tensors
def test_tf_float32(path_1, path_2):
    img_1, img_2 = _get_tf_img_arrays(path_1, path_2)
    img_1 = tf.image.convert_image_dtype(img_1, tf.float32)
    img_2 = tf.image.convert_image_dtype(img_2, tf.float32)

    value = tf.image.ssim(
        img_1, img_2, max_val=1.0, filter_size=11, filter_sigma=1.5, k1=0.01, k2=0.03
    )
    return float(value)


def _get_tf_img_arrays(path_1, path_2):
    pil_img_1, pil_img_2 = _resize_equal(path_1, path_2)
    img_1 = tf.keras.preprocessing.image.img_to_array(pil_img_1)
    img_2 = tf.keras.preprocessing.image.img_to_array(pil_img_2)

    # Add an outer batch for each image.
    img_1 = tf.expand_dims(img_1, axis=0)
    img_2 = tf.expand_dims(img_2, axis=0)
    return img_1, img_2


if __name__ == '__main__':
    freeze_support()

    # SSIM-PIL
    # Avg 0.60s, good results (match: 0.77-0.93; nonmatch: 0.26-0.45; diff: 0.32)
    # With grayscale step first: Avg 0.47s, good results (match: 0.89-0.96; nonmatch: 0.34-0.58; diff: 0.31)
    #   With GPU accelaration: avg 0.04s
    #   With multithreading + GPU accelaration: avg 0.01s
    # Dependencies: numpy, pyopencl (requires separate platform-specific OpenCL driver for GPU acceleration)
    test_ssim_func(test_ssim_pil)
    test_ssim_func__parallel(test_ssim_pil, log_results=False, executor_cls=ThreadPoolExecutor)
    # Does not work with nvidia drivers; not fork()-safe
    # test_ssim_func__parallel(test_ssim_pil, elapsed_only=True, executor_cls=ProcessPoolExecutor)
    test_ssim_func(test_ssim_pil_gpu, log_results=False)
    test_ssim_func__parallel(test_ssim_pil_gpu, log_results=False, executor_cls=ThreadPoolExecutor)
    # Does not work with nvidia drivers; not fork()-safe
    # test_ssim_func__parallel(test_ssim_pil_gpu, elapsed_only=True, executor_cls=ProcessPoolExecutor)

    # PySSIM
    # Avg 0.23s, okay results (match: 0.78-0.89; nonmatch: 0.40-0.62; diff: 0.16)
    #   With multithreading: avg 0.13s
    # Dependencies: numpy, scipy (~55MB)
    test_ssim_func(test_pyssim)
    test_ssim_func__parallel(test_pyssim, log_results=False, executor_cls=ThreadPoolExecutor)
    test_ssim_func__parallel(test_pyssim, log_results=False, executor_cls=ProcessPoolExecutor)

    # PySSIM: complex wavelet SSIM
    # Avg 3.66s good results (match: 0.77-0.86, nonmatch: 0.44-0.47; diff: 0.30)
    #   With multithreading: avg 3.41s
    #   With multiprocessing: avg 2.87s
    test_ssim_func(test_pyssim_cw)
    test_ssim_func__parallel(test_pyssim_cw, log_results=False, executor_cls=ThreadPoolExecutor)
    test_ssim_func__parallel(test_pyssim_cw, log_results=False, executor_cls=ProcessPoolExecutor)

    # scikit-image
    # Avg 0.13s, okay results (match: 0.79-0.96; nonmatch: 0.40-0.62; diff: 0.17)
    #   With multithreading: avg 0.06s
    # Dependencies: numpy, scikit-image (~30MB)
    test_ssim_func(test_scikit_image)
    test_ssim_func__parallel(test_scikit_image, log_results=False, executor_cls=ThreadPoolExecutor)
    test_ssim_func__parallel(test_scikit_image, log_results=False, executor_cls=ProcessPoolExecutor)

    # Tensorflow
    # Avg 0.33s, good results (match: 0.77-0.92; nonmatch: 0.31-0.49; diff: 0.28)
    # Dependencies: HUGE (500MB+)
    # TODO: Test with CUDA (kind of a pain to install)
    test_ssim_func(test_tf_uint8)
    test_ssim_func__parallel(test_tf_uint8, log_results=False, executor_cls=ThreadPoolExecutor)
    # test_ssim_func__parallel(test_tf_uint8, log_results=False, executor_cls=ProcessPoolExecutor)

    # Tensorflow
    # Avg 0.32s, good results, different scale (match: 0.45-0.68; nonmatch: 0.01; dif: 0.44)
    test_ssim_func(test_tf_float32)
    test_ssim_func__parallel(test_tf_float32, log_results=False, executor_cls=ThreadPoolExecutor)
    # test_ssim_func__parallel(test_tf_float32, log_results=False, executor_cls=ProcessPoolExecutor)

    # PIQ: https://github.com/photosynthesis-team/piq
    # Dependencies: pytorch, torchimage - HUUUGE (1500MB+ on Linux)
    # TODO
