"""Root Google ADK router for KJRI Dubai consular and appointment paths."""

from google.adk.agents import Agent

from agent.booking.agent import booking_agent
from agent.konsuler.agent import konsuler_agent
from agent.llm import build_model

root_agent = Agent(
    name="kjri_router",
    model=build_model(),
    description="Router menu KJRI Dubai: kekonsuleran atau janji temu.",
    instruction="""
Anda adalah router layanan chatbot KJRI Dubai. Bahasa Indonesia.

Anda tidak menjawab syarat konsuler dan tidak membuat janji temu sendiri.
Tidak ada tool domain. Serahkan ke sub-agent:

- Jika state.track == "konsuler" atau pengguna memilih
  "Cek layanan kekonsuleran", transfer ke konsuler_agent.
- Jika state.track == "janji_temu" atau pengguna memilih "Janji temu",
  transfer ke booking_agent.
- Jika track kosong, tawarkan dua menu teks:
  1. Cek layanan kekonsuleran
  2. Janji temu
  Jangan mengumpulkan identitas di langkah ini.

Jika pengguna ingin ganti jalur, kembalikan ke pilihan dua menu.
""",
    sub_agents=[konsuler_agent, booking_agent],
)
