# AUTO GENERATED FILE - DO NOT EDIT

from dash.development.base_component import Component, _explicitize_args


class Navbar(Component):
    """A Navbar component.


Keyword arguments:

- id (string; optional):
    Unique ID to identify this component in Dash callbacks.

- dashboard_name (string; required)

- dashboard_picture (string; required)

- dashboard_version (string; required)"""
    _children_props = []
    _base_nodes = ['children']
    _namespace = 'my_dash_component'
    _type = 'Navbar'
    @_explicitize_args
    def __init__(self, dashboard_name=Component.REQUIRED, dashboard_picture=Component.REQUIRED, dashboard_version=Component.REQUIRED, id=Component.UNDEFINED, **kwargs):
        self._prop_names = ['id', 'dashboard_name', 'dashboard_picture', 'dashboard_version']
        self._valid_wildcard_attributes =            []
        self.available_properties = ['id', 'dashboard_name', 'dashboard_picture', 'dashboard_version']
        self.available_wildcard_properties =            []
        _explicit_args = kwargs.pop('_explicit_args')
        _locals = locals()
        _locals.update(kwargs)  # For wildcard attrs and excess named props
        args = {k: _locals[k] for k in _explicit_args}

        for k in ['dashboard_name', 'dashboard_picture', 'dashboard_version']:
            if k not in args:
                raise TypeError(
                    'Required argument `' + k + '` was not specified.')

        super(Navbar, self).__init__(**args)
