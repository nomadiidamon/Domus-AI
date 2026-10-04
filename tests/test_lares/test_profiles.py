"""
Tests for Lares/profiles.py - AgentProfile and the registry
(register_profile/get_profile/list_profiles).

Covers: default-profile fallback for unregistered models, case-
insensitive lookup, registration/overwrite, and the exact quirks the
four shipped profiles (Mercury/Analyst/Vulcan/Minerva) are supposed to
declare - since those flags are what the rest of Lares (permissions,
response_policy, agent) actually act on, a regression here would
silently re-break the behavior those modules were written to fix.
"""

import pytest

from Lares.profiles import (
    DEFAULT_PROFILE,
    AgentProfile,
    get_profile,
    list_profiles,
    register_profile,
)

pytestmark = pytest.mark.lares


class TestRegistryBasics:
    def test_unregistered_model_gets_default_profile(self):
        assert get_profile("totally-unknown-model") is DEFAULT_PROFILE

    def test_register_then_get_round_trips(self):
        profile = AgentProfile(name="Zephyr", base_model="llama3.1:8b")
        register_profile(profile)
        try:
            assert get_profile("Zephyr") is profile
        finally:
            # Don't leak test state into other tests via the module-level
            # registry - re-register nothing (no unregister API exists
            # yet), but overwrite with a harmless default-shaped profile.
            register_profile(AgentProfile(name="Zephyr"))

    def test_lookup_is_case_insensitive(self):
        profile = AgentProfile(name="CaseTest")
        register_profile(profile)
        try:
            assert get_profile("casetest") is profile
            assert get_profile("CASETEST") is profile
            assert get_profile("CaseTest") is profile
        finally:
            register_profile(AgentProfile(name="CaseTest"))

    def test_registering_same_name_overwrites(self):
        first = AgentProfile(name="Overwrite", description="first")
        second = AgentProfile(name="Overwrite", description="second")
        register_profile(first)
        register_profile(second)
        assert get_profile("Overwrite") is second
        assert get_profile("Overwrite").description == "second"

    def test_list_profiles_returns_a_copy(self):
        snapshot = list_profiles()
        snapshot["Mercury"] = "tampered"
        # Mutating the returned dict must not affect the real registry.
        assert get_profile("Mercury").name == "Mercury"

    def test_list_profiles_includes_builtins(self):
        names = {p.name for p in list_profiles().values()}
        assert {"Mercury", "Analyst", "Vulcan", "Minerva"} <= names


class TestAgentProfileDefaults:
    def test_default_profile_is_conservative(self):
        # DEFAULT_PROFILE must not silently turn on any workaround for a
        # model nobody has vetted - these all default off/on exactly as
        # documented in AgentProfile's docstring.
        assert DEFAULT_PROFILE.supports_tool_calls is True
        assert DEFAULT_PROFILE.needs_fallback_tool_parsing is False
        assert DEFAULT_PROFILE.ground_tool_replies is False
        assert DEFAULT_PROFILE.retry_on_empty_reply is False

    def test_effective_mcp_profile_name_defaults_to_model_name(self):
        profile = AgentProfile(name="Foo")
        assert profile.effective_mcp_profile_name() == "Foo"

    def test_effective_mcp_profile_name_honors_override(self):
        profile = AgentProfile(name="Foo", mcp_profile_name="Bar")
        assert profile.effective_mcp_profile_name() == "Bar"


class TestBuiltinProfileQuirks:
    """Pin down the exact capability flags diagnosed for each shipped
    model - these are the facts the rest of Lares depends on."""

    def test_mercury_needs_fallback_tool_parsing(self):
        profile = get_profile("Mercury")
        assert profile.supports_tool_calls is True
        assert profile.needs_fallback_tool_parsing is True

    def test_analyst_has_both_response_workarounds_enabled(self):
        profile = get_profile("Analyst")
        assert profile.ground_tool_replies is True
        assert profile.retry_on_empty_reply is True

    def test_vulcan_does_not_support_tool_calls(self):
        profile = get_profile("Vulcan")
        assert profile.supports_tool_calls is False

    def test_minerva_does_not_support_tool_calls(self):
        profile = get_profile("Minerva")
        assert profile.supports_tool_calls is False