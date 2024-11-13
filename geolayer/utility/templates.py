import inspect
import os

MASKS_PATH = os.path.join(os.path.dirname(__file__), '../masks')


def load_template(mask_name):
    with open(os.path.join(MASKS_PATH, '{}.xml'.format(mask_name)), 'r') as f:
        return f.read()


def fill_template(mask_str, **kwargs):
    return mask_str.format(**kwargs)
