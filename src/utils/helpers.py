def get_leaf_classes(base_class):
  """
  Gets all the leaf classes (classes with no subclasses) in an inheritance 
  structure, starting from a base class.

  Args:
    base_class: The base class of the inheritance structure.

  Returns:
    A list of leaf classes.
  """
  leaf_classes = []
  subclasses = base_class.__subclasses__()
  if not subclasses:
    leaf_classes.append(base_class)
  else:
    for subclass in subclasses:
      leaf_classes.extend(get_leaf_classes(subclass))
  return leaf_classes