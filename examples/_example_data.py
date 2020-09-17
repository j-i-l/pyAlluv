import json

eg_data = [
    # slice 0: initial state
    {'a': {None: 10}, 'b': {None: 14}, 'c': {None: 4}},
    # slice 1
    {
        None: {'a': 1},
        'a': {'a': 4},
        'b': {'a': 6},
        'c': {'b': 8},
        'd': {'b': 5},
        'e': {'c': 4, None: 4}
        },
    # slice 2
    {
        None: {'b': 1, 'c': 3, 'd': 2, 'e': 1},
        'a': {'b': 5},
        'b': {'a': 3, 'c': 5, 'd': 1},
        'c': {'e': 3},
        'd': {'e': 4}
        },
    # slice 3
    {
        None: {'b': 2},
        'a': {'a': 5, None: 4},
        'b': {'b': 3},
        'c': {'b': 5},
        'd': {'c': 3},
        'e': {'c': 1, 'd': 1},
        'f': {'d': 4}
        },
    # slice 4
    {
        None: {'a': 1, 'c': 1, 'd': 1},
        'a': {'a': 5},
        'b': {'a': 3, 'b': 1},
        'c': {'b': 2, 'c': 4},
        'd': {'d': 2, 'e': 2, 'f': 4}
        },
    # slice 5
    {
        None: {},
        'a': {'a': 5, 'b': 4, None: 1},
        'b': {'c': 6, 'd': 8}
        }
]

with open('example_data.json', 'w') as fobj:
    json.dump(eg_data, fobj)
