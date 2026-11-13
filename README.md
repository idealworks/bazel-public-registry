# Bazel Public Registry

## Overview

Bazel registry for the publicly available source code projects used within idealworks

> The version names on `master` predate the scheme below and can sort in the wrong order under
> Bazel (e.g. `2.2.4-4-gb70b71b.iw.jazzy.0` sorts *below* `2.2.4.iw.jazzy.1`). `master` is
> deprecated for anyone who still needs those names.

## Version names

A module built from a git commit is named after `git describe --tags --long` of that commit:

```
<tag>                 e.g.  3.2.0           upstream as-is, exactly at the tag
<tag>.<N>                   3.2.0.2         upstream as-is, N commits after the tag
<tag>.<N>.iw.<K>            3.2.0.0.iw.0    we add an overlay or patches (N may be 0)
```

- `<tag>`: the tag, with any project prefix dropped (`libXau-1.0.12` -> `1.0.12`), `-`/`_` turned
  into `.`, a leading `v` dropped. When anything follows it, it is padded to three parts
  (`v257` -> `257.0.0`) so `<N>` is always the fourth part. Bazel ranks a letter above a digit,
  so `v1.0.6...` would outrank the BCR's `1.0.7` of the same module.
- `<N>`: commits since the tag, written after a `.`, so Bazel compares it as a number. A `-`
  there would make the version a Bazel prerelease that sorts below `<tag>` itself.
- `.iw.<K>`: our build of that commit. Bump `K` when only the registry entry changes
  (patches, overlay, deps). No commit hash and no distro: `<tag>.<N>` already pins the commit
  on the branch the module tracks.

`scripts/apply_ws_module_to_registry.py` enforces this for modules whose describe starts with a
digit: anything staged in the module's checkout counts as an overlay or patch. Untagged repos
are named as if their root commit were tagged `0.0.0`.

Exceptions: release tarballs (no git history) keep the upstream release version. `fast_cdr` is
named after its CMake project version (`2.2.8.iw.0`), because eProsima tags releases on
side branches, so `git describe` on the `2.2.x` branch Jazzy tracks prints `v2.0.0-N-g...`.

