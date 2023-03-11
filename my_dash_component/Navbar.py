# AUTO GENERATED FILE - DO NOT EDIT

from dash.development.base_component import Component, _explicitize_args


class Navbar(Component):
    """A Navbar component.


Keyword arguments:

- id (string; optional):
    Unique ID to identify this component in Dash callbacks.

- uni_name (string; default 'University Name')

- uni_picture (string; default 'https://cdn-icons-png.flaticon.com/512/2231/2231696.png')

- version (string; default 'Unknown version')"""
    _children_props = []
    _base_nodes = ['children']
    _namespace = 'my_dash_component'
    _type = 'Navbar'
    @_explicitize_args
    def __init__(self, uni_name=Component.UNDEFINED, uni_picture=Component.UNDEFINED, version=Component.UNDEFINED, id=Component.UNDEFINED, **kwargs):
        self._prop_names = ['id', 'uni_name', 'uni_picture', 'version']
        self._valid_wildcard_attributes =            []
        self.available_properties = ['id', 'uni_name', 'uni_picture', 'version']
        self.available_wildcard_properties =            []
        _explicit_args = kwargs.pop('_explicit_args')
        _locals = locals()
        _locals.update(kwargs)  # For wildcard attrs and excess named props
        args = {k: _locals[k] for k in _explicit_args}

        super(Navbar, self).__init__(**args)
