# AUTO GENERATED FILE - DO NOT EDIT

from dash.development.base_component import Component, _explicitize_args


class Grid(Component):
    """A Grid component.


Keyword arguments:

- children (list of a list of or a singular dash component, string or numbers; required)

- id (string; optional):
    Unique ID to identify this component in Dash callbacks.

- hash (string; required)"""
    _children_props = []
    _base_nodes = ['children']
    _namespace = 'my_dash_component'
    _type = 'Grid'
    @_explicitize_args
    def __init__(self, children=None, hash=Component.REQUIRED, id=Component.UNDEFINED, **kwargs):
        self._prop_names = ['children', 'id', 'hash']
        self._valid_wildcard_attributes =            []
        self.available_properties = ['children', 'id', 'hash']
        self.available_wildcard_properties =            []
        _explicit_args = kwargs.pop('_explicit_args')
        _locals = locals()
        _locals.update(kwargs)  # For wildcard attrs and excess named props
        args = {k: _locals[k] for k in _explicit_args if k != 'children'}

        for k in ['hash']:
            if k not in args:
                raise TypeError(
                    'Required argument `' + k + '` was not specified.')

        if 'children' not in _explicit_args:
            raise TypeError('Required argument children was not specified.')

        super(Grid, self).__init__(children=children, **args)
