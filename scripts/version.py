"""Encapsulation of the bzlmod Module description"""

import os
import re
import unittest
from dataclasses import dataclass
from itertools import zip_longest
from typing import ClassVar


@dataclass(frozen=True)
class Identifier:
    """
    A single identifier in a Bzlmod version string. It can be either digits only
    or alphanumeric. Digit-only versions come before alphanumeric versions.

    Reference: https://cs.opensource.google/bazel/bazel/+/master:src/main/java/com/google/devtools/build/lib/bazel/bzlmod/Version.java;l=94
    """

    digits_only: bool
    as_int: int
    as_str: str

    @classmethod
    def parse(cls, identifier: str):
        if not identifier:
            raise ValueError("Empty identifier")
        if identifier.isdigit():
            return cls(digits_only=True, as_int=int(identifier), as_str=identifier)
        return cls(digits_only=False, as_int=0, as_str=identifier)

    def __lt__(self, other):
        if self.digits_only:
            if other.digits_only:
                return self.as_int < other.as_int
            return True
        if other.digits_only:
            return False
        return self.as_str < other.as_str


@dataclass(frozen=True)
class Version:
    """
    Implementation of the Bzlmod versioning format.
    Reference: https://cs.opensource.google/bazel/bazel/+/master:src/main/java/com/google/devtools/build/lib/bazel/bzlmod/Version.java;l=33

    The basic format is RELEASE[-PRERELEASE][+BUILD], although people seem to abuse
    the format in various ways. RELEASE and PRERELEASE are dot-separated sequences of
    alphanumeric strings. We don't care about BUILD. To compare, we compare each
    segment of RELEASE and PRERELEASE lexicographically. Versions without prerelease
    are always greater than versions with prerelease.
    """

    PATTERN: ClassVar = re.compile(
        r"(?P<release>[a-zA-Z0-9.]+)(?:-(?P<prerelease>[a-zA-Z0-9.-]+))?(?:\+[a-zA-Z0-9.-]+)?"
    )

    release: tuple[Identifier, ...]
    prerelease: tuple[Identifier, ...]
    normalized: str

    @classmethod
    def parse(cls, version_str: str):
        if not (match := cls.PATTERN.match(version_str)):
            raise ValueError(f"Invalid version string: {version_str}")

        release_str = match.group("release")
        prerelease_str = match.group("prerelease")

        release_tuple = tuple(Identifier.parse(x) for x in release_str.split("."))
        if prerelease_str:
            prerelease_tuple = tuple(
                Identifier.parse(x) for x in prerelease_str.split(".")
            )
        else:
            prerelease_tuple = ()

        normalized = (
            f"{release_str}-{prerelease_str}" if prerelease_str else release_str
        )
        return cls(
            release=release_tuple, prerelease=prerelease_tuple, normalized=normalized
        )

    @classmethod
    def empty(cls):
        return cls(release=(), prerelease=(), normalized="")

    def __bool__(self):
        return not self.is_empty()

    def is_empty(self):
        """Return whether the version is empty"""
        return not self.normalized

    def __lt__(self, other):
        # comparing(Version::isEmpty, falseFirst())
        if not self:
            return True
        if not other:
            return False

        # thenComparing(Version::release, lexicographical(Identifier.COMPARATOR))
        for self_id, other_id in zip_longest(self.release, other.release):
            if self_id is None:
                return True
            if other_id is None:
                return False

            if self_id < other_id:
                return True
            if other_id < self_id:
                return False

        # thenComparing(Version::isPrerelease, trueFirst())
        if not self.prerelease:
            return False
        if not other.prerelease:
            return True

        # thenComparing(Version::prerelease, lexicographical(Identifier.COMPARATOR))
        for self_id, other_id in zip_longest(self.prerelease, other.prerelease):
            if self_id is None:
                return True
            if other_id is None:
                return False

            if self_id < other_id:
                return True
            if other_id < self_id:
                return False

        # Equal, so not less.
        return False

    def __str__(self):
        return self.normalized

    def __repr__(self):
        return f"Version({self.normalized})"


class TestVersion(unittest.TestCase):
    # 8.8.0.bcr.1 -> 8.7.1
    def test_non_match_override(self):
        self.assertLess(Version.parse("8.7.1"), Version.parse("8.8.0.bcr.1"))

    def test_version_cmp(self):
        self.assertLess(Version.parse("0.37.0"), Version.parse("1.0.0-rc0"))

    def test_orocos_version(self):
        self.assertLess(
            Version.parse("0.7.0-1-gb86d2da"), Version.parse("1.5.1.40.g507de66.iw.1")
        )
