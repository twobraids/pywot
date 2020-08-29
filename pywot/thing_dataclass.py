import logging

from dataclasses import dataclass, make_dataclass

DoNotCare = None

types = {
    "null": None,
    "boolean": bool,
    "object": object,
    "array": list,
    "number": float,
    "integer": int,
    "string": str,
}


class ThingDataClassBase:
    def _a_comparitor(self, other, compare_fn):
        if not isinstance(self, other.__class__):
            raise TypeError
        result = True
        for self_meta_prop, other_meta_prop in zip(self.meta, other.meta):
            self_property_name, self_property_type = self_meta_prop
            other_property_name, other_property_type = other_meta_prop
            self_property_value = getattr(self, self_property_name)
            if self_property_value is DoNotCare:
                continue
            other_property_value = getattr(other, other_property_name)
            if other_property_value is DoNotCare:
                continue
            result = result and compare_fn(self_property_value, other_property_value)
        return result

    def _hash_fn(self):
        data = []
        for self_meta_prop in self.meta:
            self_property_name, self_property_type = self_meta_prop
            data.append(getattr(self, self_property_name))
        data_tuple = tuple(data)
        return hash(data_tuple)

    def as_dict(self):
        d = {}
        for self_meta_prop in self.meta:
            self_property_name, self_property_type = self_meta_prop
            value = getattr(self, self_property_name)
            if value is not DoNotCare:
                d[self_property_name] = value
        return d

    @classmethod
    def kwargs_from_thing(klass, a_thing):
        d = {}
        for self_meta_prop in klass.meta:
            self_property_name, self_property_type = self_meta_prop
            d[self_property_name] = getattr(a_thing, self_property_name)
        return d

    def __eq__(self, other):
        return self._a_comparitor(other, lambda a, b: a == b)

    def __ne__(self, other):
        return self._a_comparitor(other, lambda a, b: a != b)

    def __lt__(self, other):
        return self._a_comparitor(other, lambda a, b: a < b)

    def __le__(self, other):
        return self._a_comparitor(other, lambda a, b: a <= b)

    def __gt__(self, other):
        return self._a_comparitor(other, lambda a, b: a > b)

    def __ge__(self, other):
        return self._a_comparitor(other, lambda a, b: a >= b)


def create_dataclass(name, a_thing_meta):
    a_thing_meta_properties = a_thing_meta["properties"]
    fields = []
    for key in a_thing_meta_properties.keys():
        try:
            fields.append((key, types[a_thing_meta_properties[key]["type"]]))
        except KeyError as e:
            logging.info(f"Error: property {key} has no {e}, ignoring it")

    thing_dataclass = make_dataclass(
        name,
        fields,
        bases=(ThingDataClassBase,),
        namespace={"__hash__": lambda self: self._hash_fn()},
        frozen=True,
    )
    thing_dataclass.meta = fields
    return thing_dataclass
