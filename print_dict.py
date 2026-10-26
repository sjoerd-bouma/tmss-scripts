#!/usr/bin/env python3

def print_dict(v, prefix=''):
    if isinstance(v, dict):
        for k, v2 in v.items():
            p2 = "{}['{}']".format(prefix, k)
            print_dict(v2, p2)
    elif isinstance(v, list):
        for i, v2 in enumerate(v):
            p2 = "{}[{}]".format(prefix, i)
            print_dict(v2, p2)
    else:
        print('{} = {}'.format(prefix, repr(v)))

def replace_matching_values(output_dict, input_dict):
    for key, value in input_dict.items():
        if key not in output_dict:
            continue

        if isinstance(value, dict) and isinstance(output_dict[key], dict):
            replace_matching_values(output_dict[key], value)
        else:
            output_dict[key] = value
