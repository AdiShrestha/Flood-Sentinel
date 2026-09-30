# This file has moved

As of Factory v2.2.0, the Architect's operating document is **`architect_spec.md`**, in this same directory. Attach that file instead.

This pointer exists only so a bootstrap script or muscle memory pointed at the old filename doesn't hit a missing file. It has no operational content of its own and `gatekeeper.py self-check` reads `architect_spec.md` directly, not this file. See `CHANGELOG.md`'s v2.2.0 entry for why the rename happened (adopting "Architect"/"Implementor" as the primary role names, matching `implementor_spec.md`'s v2.0.0 precedent) and `dynamic_rules.md`/`architect_spec.md` §9 for why the separate `role_bindings.yaml` reference this file used to carry alongside it was removed rather than carried forward — it never had any backing infrastructure.
