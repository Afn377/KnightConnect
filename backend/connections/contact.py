def shared_contact_methods(user):
    """Contact details revealed to the other side of an accepted connection.

    Falls back to the student's verified Rutgers email when they have not
    added any contact methods, so an accepted connection is always reachable.
    """
    methods = [{"kind": method.kind, "value": method.value} for method in user.contact_methods.all()]
    return methods or [{"kind": "email", "value": user.email}]
