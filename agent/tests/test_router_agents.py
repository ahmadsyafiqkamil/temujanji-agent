from agent.agent import root_agent
from agent.booking.agent import booking_agent
from agent.konsuler.agent import konsuler_agent


def _tool_names(agent) -> set[str]:
    names: set[str] = set()
    for tool in getattr(agent, "tools", None) or []:
        name = getattr(tool, "name", None) or getattr(tool, "__name__", None)
        if name:
            names.add(name)
    return names


def test_root_agent_is_router_without_domain_tools():
    assert _tool_names(root_agent) == set()
    sub_names = {agent.name for agent in root_agent.sub_agents}
    assert sub_names == {"konsuler_agent", "booking_agent"}


def test_booking_agent_only_exposes_appointment_tools():
    assert booking_agent.name == "booking_agent"
    assert _tool_names(booking_agent) == {
        "list_services",
        "get_availability",
        "create_appointment",
        "cancel_appointment",
    }
    assert "cari_layanan" not in _tool_names(booking_agent)
    instruction = booking_agent.instruction.lower()
    assert "janji temu" in instruction
    assert "bahasa indonesia" in instruction
    assert "always communicate in clear" not in instruction


def test_konsuler_agent_only_exposes_konsuler_tools():
    assert konsuler_agent.name == "konsuler_agent"
    assert _tool_names(konsuler_agent) == {
        "cari_layanan",
        "get_detail_layanan",
        "cari_layanan_semantik",
        "simpan_identitas",
        "simpan_interaksi",
    }
    assert "create_appointment" not in _tool_names(konsuler_agent)
    assert (
        "schema konsuler" in konsuler_agent.instruction.lower()
        or "kekonsuleran" in konsuler_agent.instruction.lower()
    )
