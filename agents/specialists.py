"""agents/specialists.py.

The six specialist agent configurations for UAS component research.

WHY SEPARATE CONFIG FROM INFRASTRUCTURE?
The prompts and schemas here are "what the agents know about their domain."
The BaseAgent in base.py is "how agents run." Keeping these separate means:
  - You can tune a prompt without touching infrastructure code
  - You can add a 7th specialist by adding one entry here
  - You can test prompts independently of the API call logic

This is the Config-as-Code pattern, common in production ML/AI systems.

PROJECT CONTEXT (injected into every agent's system prompt)
This shared context block ensures every specialist reasons within
the same constraints. It's equivalent to a shared project brief in
a human team.
"""

from .base import AgentConfig
from .team import AgentTeamConfig

# ---------------------------------------------------------------------------
# Shared project context — injected into every agent's system prompt.
# Centralizing this means updating constraints in one place propagates
# to all agents automatically.
# ---------------------------------------------------------------------------

PROJECT_CONTEXT = """
## Project Context (read carefully — all recommendations must satisfy these constraints)

You are a specialist researcher contributing to a UAS build project with these fixed constraints:

- **Budget**: $200-400 USD total for all hardware (RC radio included)
- **Primary mission**: AI perception experiments — computer vision, object tracking,
  visual odometry — NOT freestyle FPV or cinematic photography
- **Companion computer**: Raspberry Pi Zero 2W (already owned, not in budget)
  - 512MB RAM, quad-core ARM Cortex-A53 @ 1GHz
  - UART, I2C, SPI, CSI (camera) interfaces available
  - Must be physically mountable on the chosen frame
- **Frame size**: Sub-5" (3" to 4" prop diameter preferred for sub-250g goal)
- **Firmware**: ArduPilot (NOT BetaFlight) — autonomous waypoint navigation required
- **RC system**: Starting fresh, no existing radio. Prefer ELRS ecosystem.
- **Scalability priorities**:
  1. Sensor expansion (LiDAR, optical flow, second camera, GPS)
  2. Clean Python/MCP software architecture for agentic control
- **Builder skill**: Comfortable soldering, first UAS build
- **Key constraint**: Pi Zero 2W must receive the camera feed digitally
  (analog FPV cameras that bypass the Pi are acceptable for piloting,
  but the CV pipeline camera MUST feed into the Pi's CSI or USB port)
"""

# ---------------------------------------------------------------------------
# Output schema instructions — appended to every user prompt.
# Defining this once and reusing it enforces consistency.
# ---------------------------------------------------------------------------

JSON_OUTPUT_INSTRUCTION = """
## Output Format

You MUST end your response with a JSON block wrapped in ```json ... ``` fences.
The JSON must be complete and valid. Do not truncate it.
Research thoroughly first (use web search liberally), then produce the JSON.
Include specific product names, current prices from US retailers (GetFPV,
RaceDayQuads, Amazon, Rotor Riot), and direct purchase URLs where possible.
"""


# ---------------------------------------------------------------------------
# Specialist Agent 1: Frame & Mechanical
# ---------------------------------------------------------------------------

FRAME_AGENT = AgentConfig(
    name="Frame & Mechanical Agent",
    domain="frame_mechanical",
    system_prompt=f"""You are a specialist in micro FPV/UAS frame design and mechanical integration.
Your expertise covers frame geometry, weight budgets, mounting systems, and component fitment
for sub-5" builds. You are deeply familiar with the constraints of fitting companion computers
(specifically Raspberry Pi Zero 2W form factor: 65mm x 30mm) inside or on top of micro frames.

{PROJECT_CONTEXT}

Your task: Research and recommend the best frame options for this build.
Focus on:
1. Internal volume and stack height sufficient for: FC (20x20 or 30x30), ESC, Pi Zero 2W, VTX
2. Weight — target under 80g for the frame itself to keep all-up weight under 250g
3. Documented companion computer mounting solutions (top plate, extra standoffs)
4. Durability for test flights with expensive electronics aboard
5. Availability from US retailers with current pricing

Research at least 5 frames before making your recommendation.
""",
    user_prompt=f"""Research sub-5" ArduPilot-compatible UAS frames suitable for AI perception missions
with a Raspberry Pi Zero 2W companion computer.

Key questions to answer:
1. What 3-4" frames have enough internal volume for a Pi Zero 2W (65mm x 30mm board)?
2. Which frames use 20x20 or 30x30 FC stack mounting?
3. What is the realistic all-up weight target for a sub-250g build with full sensor suite?
4. Are there frames specifically designed with companion computer mounting in mind?
5. What's the strongest community/vendor support for replacement parts?

Search for: "3 inch fpv frame companion computer mount", "4 inch fpv frame ardupilot",
"sub 250g autonomous drone frame", current pricing on GetFPV and RaceDayQuads.

{JSON_OUTPUT_INSTRUCTION}

Required JSON structure:
{{
  "top_recommendation": {{
    "name": "Frame name",
    "manufacturer": "Manufacturer",
    "prop_size": "3\" or 4\"",
    "stack_mounting": "20x20 or 30x30",
    "weight_grams": 0,
    "price_usd": 0.0,
    "purchase_url": "https://...",
    "pi_zero_mounting": "Description of how Pi Zero 2W mounts",
    "internal_volume_notes": "Description",
    "pros": ["pro1", "pro2"],
    "cons": ["con1", "con2"]
  }},
  "alternatives": [
    {{
      "name": "Frame name",
      "prop_size": "3\" or 4\"",
      "weight_grams": 0,
      "price_usd": 0.0,
      "purchase_url": "https://...",
      "why_considered": "Brief rationale"
    }}
  ],
  "weight_budget_estimate": {{
    "frame_grams": 0,
    "fc_esc_grams": 0,
    "motors_x4_grams": 0,
    "battery_grams": 0,
    "pi_zero_2w_grams": 31,
    "gps_module_grams": 0,
    "camera_module_grams": 0,
    "vtx_grams": 0,
    "receiver_grams": 0,
    "wiring_misc_grams": 15,
    "total_estimated_grams": 0,
    "sub_250g_achievable": true
  }},
  "mounting_strategy": "Detailed description of physical integration approach"
}}
""",
    output_schema={},
)


# ---------------------------------------------------------------------------
# Specialist Agent 2: Flight Controller & ArduPilot
# ---------------------------------------------------------------------------

FC_AGENT = AgentConfig(
    name="Flight Controller Agent",
    domain="flight_controller",
    system_prompt=f"""You are a specialist in flight controller hardware and ArduPilot firmware configuration.
You have deep expertise in: FC processor generations (F4 vs F7 vs H7), UART allocation,
ArduPilot's hardware abstraction layer, and the specific requirements for running ArduPilot
on micro FCs vs the traditional larger form factors it was designed for.

{PROJECT_CONTEXT}

Your task: Identify the best ArduPilot-compatible flight controllers for this build.

Critical requirements:
- ArduPilot support must be OFFICIAL and CURRENT (not experimental or abandoned ports)
- Minimum 4 UARTs needed: GPS, MAVLink companion link, RC input (SBUS/CRSF), telemetry radio
- H7 processor strongly preferred over F7/F4 for ArduPilot's heavier processing requirements
- 20x20 or 30x30 mounting pattern to fit micro frames
- Current production availability (not discontinued)

Common pitfall to research: Many FCs marketed as "ArduPilot compatible" have community ports
that are abandoned or broken in current ArduPilot releases. Verify active support.
""",
    user_prompt=f"""Research ArduPilot-compatible flight controllers in 20x20 or 30x30 form factor
suitable for a sub-5" autonomous UAS with a companion computer.

Key questions to answer:
1. Which micro FCs have OFFICIAL ArduPilot support with active maintenance in 2024-2025?
2. Which have H7 processors (preferred for ArduPilot over F4/F7)?
3. How many UARTs does each have and how should they be allocated for this build?
4. Are there dedicated ArduPilot micro FC options (Matek, Holybro, etc.)?
5. What are the known ArduPilot issues with each candidate?

UART allocation needed:
- UART 1: GPS (u-blox M10)
- UART 2: MAVLink serial link to Pi Zero 2W (57600 baud)
- UART 3: RC input (ExpressLRS receiver, CRSF protocol)
- UART 4: Telemetry radio (SiK 915MHz, optional but desired)
- UART 5: Optical flow sensor (optional, Phase 2)

Search: "ardupilot h7 20x20 flight controller 2024", "matek ardupilot micro",
"holybro kakute mini ardupilot", "ardupilot supported targets 20x20"

{JSON_OUTPUT_INSTRUCTION}

Required JSON structure:
{{
  "top_recommendation": {{
    "name": "FC name",
    "manufacturer": "Manufacturer",
    "processor": "STM32H743 or similar",
    "mounting": "20x20 or 30x30",
    "uart_count": 0,
    "weight_grams": 0,
    "price_usd": 0.0,
    "purchase_url": "https://...",
    "ardupilot_target_name": "e.g. MatekH743-mini",
    "ardupilot_support_status": "Official/Community/Experimental",
    "uart_allocation": {{
      "uart1": "GPS",
      "uart2": "MAVLink to Pi Zero 2W",
      "uart3": "ELRS RC input",
      "uart4": "Telemetry or optical flow",
      "uart5": "Available for expansion"
    }},
    "integrated_features": ["Barometer", "IMU model", "OSD", "BEC voltage"],
    "known_ardupilot_issues": ["issue1 if any"],
    "pros": ["pro1", "pro2"],
    "cons": ["con1", "con2"]
  }},
  "alternatives": [
    {{
      "name": "FC name",
      "processor": "...",
      "uart_count": 0,
      "price_usd": 0.0,
      "purchase_url": "https://...",
      "ardupilot_support_status": "...",
      "why_considered": "Brief rationale"
    }}
  ],
  "ardupilot_configuration_notes": "Key ArduPilot params to set for companion computer integration",
  "mavlink_companion_setup": "How to configure MAVLink serial on this FC for Pi Zero 2W"
}}
""",
    output_schema={},
)


# ---------------------------------------------------------------------------
# Specialist Agent 3: Propulsion System
# ---------------------------------------------------------------------------

PROPULSION_AGENT = AgentConfig(
    name="Propulsion Agent",
    domain="propulsion",
    system_prompt=f"""You are a specialist in micro UAS propulsion — motors, ESCs, propellers, and batteries
for sub-5" autonomous platforms. You understand the tradeoffs between efficiency (flight time),
stability (hover quality for CV missions), and durability (crash survivability during testing).

{PROJECT_CONTEXT}

Your task: Recommend a complete propulsion stack for a stable-hover AI perception platform.

Design philosophy for this mission:
- Optimize for STABLE HOVER, not snap rolls. 3:1 thrust-to-weight ratio at hover,
  not the 10:1 ratios of freestyle builds. Overpowered motors cause instability at hover.
- Optimize for FLIGHT TIME over peak performance. CV experiments need 8-12 minute flights.
- Motor KV should be appropriate for chosen prop size and 3S/4S battery.
- ESC must support BLHeli_32 or AM32 with telemetry (RPM data back to FC is valuable
  for ArduPilot's motor health monitoring).
""",
    user_prompt=f"""Research a complete propulsion system for a sub-250g autonomous AI perception UAS
with 3" or 4" props (matching the frame recommendation) designed for stable hover.

Key questions:
1. What motor KV and size is appropriate for stable hover on 3" vs 4" builds?
2. What ESC options provide telemetry feedback to ArduPilot?
3. What battery chemistry, cell count, and capacity gives 8-10 minute flight time?
4. What props are known for low vibration (critical for IMU quality in ArduPilot)?
5. What is the all-up thrust and estimated hover throttle percentage?

Design targets:
- All-up weight: ~200-230g
- Hover at 40-50% throttle (efficiency sweet spot)
- 8+ minute flight time
- Low vibration props (vibration degrades ArduPilot's EKF/IMU performance)

Search: "3 inch motor stable hover autonomous", "4 inch 1404 motor ardupilot",
"micro quad 4s battery flight time", "blheli_32 esc telemetry ardupilot",
"low vibration props 3 inch 4 inch fpv"

{JSON_OUTPUT_INSTRUCTION}

Required JSON structure:
{{
  "motors": {{
    "name": "Motor name",
    "manufacturer": "Manufacturer",
    "stator_size": "1404 or similar",
    "kv": 0,
    "weight_grams_each": 0,
    "price_usd_each": 0.0,
    "set_of_4_price_usd": 0.0,
    "purchase_url": "https://...",
    "recommended_prop_size": "3\" or 4\"",
    "max_thrust_grams": 0,
    "rationale": "Why this motor for stable hover CV missions"
  }},
  "esc": {{
    "name": "ESC name",
    "type": "4-in-1 preferred",
    "firmware": "BLHeli_32 or AM32",
    "current_rating_amps": 0,
    "telemetry_support": true,
    "mounting": "20x20 or 30x30",
    "weight_grams": 0,
    "price_usd": 0.0,
    "purchase_url": "https://..."
  }},
  "battery": {{
    "chemistry": "LiPo or LiHV",
    "cell_count": "3S or 4S",
    "capacity_mah": 0,
    "c_rating": 0,
    "weight_grams": 0,
    "price_usd": 0.0,
    "purchase_url": "https://...",
    "estimated_flight_time_minutes": 0
  }},
  "props": {{
    "name": "Prop name",
    "size_pitch": "3x1.9 or similar",
    "weight_grams_each": 0,
    "price_usd_set": 0.0,
    "purchase_url": "https://...",
    "vibration_characteristics": "Notes on vibration profile"
  }},
  "propulsion_summary": {{
    "total_propulsion_cost_usd": 0.0,
    "total_propulsion_weight_grams": 0,
    "estimated_max_thrust_grams": 0,
    "hover_throttle_percent": 0,
    "estimated_flight_time_minutes": 0
  }}
}}
""",
    output_schema={},
)


# ---------------------------------------------------------------------------
# Specialist Agent 4: RC Link & Telemetry
# ---------------------------------------------------------------------------

RC_TELEMETRY_AGENT = AgentConfig(
    name="RC & Telemetry Agent",
    domain="rc_telemetry",
    system_prompt=f"""You are a specialist in RC link systems, telemetry radios, and ground control station
integration for ArduPilot-based UAS. You have deep expertise in ExpressLRS (ELRS) ecosystem,
MAVLink protocol, SiK telemetry radios, and Mission Planner/QGroundControl configuration.

{PROJECT_CONTEXT}

Your task: Recommend the complete RC and telemetry stack for a first-time builder.

Key considerations:
- Budget consciousness: This is the highest risk area for overspending.
  RadioMaster has excellent value options. Avoid DJI remote controllers.
- ELRS is the correct choice for a new builder in 2025 — best range, open source,
  large community, natively supported by ArduPilot via CRSF protocol.
- A SiK telemetry radio pair (915MHz in US) is highly valuable for ArduPilot —
  it lets Mission Planner connect to the drone over WiFi/radio during autonomous flights,
  enabling parameter tuning, mission upload, and live telemetry without USB.
- MAVLink RC override via the telemetry link is how the Pi Zero 2W sends autonomous
  commands to ArduPilot without needing a separate radio link.
""",
    user_prompt=f"""Research the complete RC transmitter, receiver, and telemetry radio stack for a
first-time builder starting fresh with ELRS, budget $70-90 for radio + receiver + telemetry.

Key questions:
1. What RadioMaster ELRS transmitter is best value for a new builder under $60?
2. What ELRS receivers are smallest/lightest and ArduPilot CRSF-compatible?
3. What SiK 915MHz telemetry radio pairs are available under $30?
4. How does MAVLink RC override work via the Pi companion computer?
5. What is the correct ArduPilot configuration for ELRS CRSF input?

The telemetry radio serves double duty:
- Ground station connectivity (Mission Planner on laptop)
- MAVLink RC override channel for Pi Zero 2W autonomous commands

Search: "radiomaster pocket elrs price 2024", "radiomaster zorro elrs",
"expresslrs receiver nano crsf ardupilot", "sik telemetry radio 915mhz ardupilot",
"holybro sik radio v3"

{JSON_OUTPUT_INSTRUCTION}

Required JSON structure:
{{
  "transmitter": {{
    "name": "TX name",
    "manufacturer": "RadioMaster or other",
    "protocol": "ELRS",
    "form_factor": "Full size / Lite / Gamepad",
    "internal_elrs_module": true,
    "elrs_version": "3.x",
    "weight_grams": 0,
    "price_usd": 0.0,
    "purchase_url": "https://...",
    "recommended_for_beginner": true,
    "rationale": "Why this TX"
  }},
  "receiver": {{
    "name": "RX name",
    "manufacturer": "...",
    "protocol": "ELRS CRSF",
    "weight_grams": 0,
    "price_usd": 0.0,
    "purchase_url": "https://...",
    "ardupilot_uart_config": "SERIAL_PROTOCOL value and baud rate",
    "antenna_type": "Ceramic/Dipole/etc"
  }},
  "telemetry_radio": {{
    "name": "Radio name",
    "frequency_mhz": 915,
    "protocol": "SiK MAVLink",
    "range_km_typical": 0.0,
    "price_usd_pair": 0.0,
    "purchase_url": "https://...",
    "ardupilot_config": "SERIAL_PROTOCOL and baud rate settings",
    "pi_zero_integration": "How Pi Zero 2W connects to drone-side radio"
  }},
  "mavlink_rc_override_notes": "Explanation of how Pi Zero 2W sends autonomous commands via MAVLink",
  "total_rc_telemetry_cost_usd": 0.0,
  "total_weight_grams": 0
}}
""",
    output_schema={},
)


# ---------------------------------------------------------------------------
# Specialist Agent 5: Vision & Perception Stack
# ---------------------------------------------------------------------------

VISION_AGENT = AgentConfig(
    name="Vision & Perception Agent",
    domain="vision_perception",
    system_prompt=f"""You are a specialist in embedded computer vision, edge AI inference, and camera systems
for resource-constrained platforms. You have deep expertise in:
- Raspberry Pi camera ecosystem (Camera Module v2, v3, HQ, NoIR variants)
- Lightweight CV frameworks: TFLite, OpenCV on ARM, NCNN, Hailo-8L
- Performance benchmarks for inference on Pi Zero 2W vs Pi 4/5
- FPV video transmission systems and their camera interfaces
- Visual odometry and optical flow for GPS-denied navigation

{PROJECT_CONTEXT}

Your task: Design the complete vision and perception stack.

CRITICAL CONSTRAINT: The Pi Zero 2W has 512MB RAM and a slow quad-core A53.
Be honest about its limitations for real-time inference. Benchmarks matter here.
Do NOT recommend architectures that will run at 0.5 FPS — that's not useful.

Camera strategy for this build (two separate cameras):
1. CV CAMERA: Pi Camera Module → CSI port on Pi Zero 2W → inference pipeline
2. FPV CAMERA: Analog camera → VTX → pilot's goggles (bypasses Pi entirely)
This separation is deliberate: analog FPV has ~1ms latency, digital has 20-100ms.
The pilot gets analog; the AI gets its own clean CSI feed.
""",
    user_prompt=f"""Research the complete vision and perception stack for AI experiments on a Pi Zero 2W.

Key questions:
1. Which Pi Camera Module (v2, v3, HQ, NoIR) is best for CV experiments at this budget?
2. What are real-world inference benchmarks for MobileNetV2, YOLOv5n, YOLOv8n on Pi Zero 2W?
3. Is TFLite or NCNN faster on the Pi Zero 2W's ARM Cortex-A53?
4. What analog FPV camera + VTX combination is best under $25 combined?
5. What is a realistic CV pipeline architecture given the Pi Zero 2W's constraints?
6. Is a Hailo-8L or similar AI accelerator worth considering for Phase 2?
7. How should the Python CV pipeline be structured for the agentic control loop?

For the analog FPV system: the pilot needs to see to fly, but keeping it analog
keeps cost and weight low. The AI camera is separate and digital (CSI port).

Search: "raspberry pi zero 2w tensorflow lite benchmark fps",
"raspberry pi camera module v3 vs v2 opencv", "yolov5n pi zero 2w inference speed",
"analog fpv camera vtx lightweight cheap 2024", "ncnn arm cortex a53 benchmark",
"hailo 8l raspberry pi zero"

{JSON_OUTPUT_INSTRUCTION}

Required JSON structure:
{{
  "cv_camera": {{
    "name": "Pi Camera Module X",
    "sensor": "IMX...",
    "resolution": "...",
    "interface": "CSI",
    "fov_degrees": 0,
    "weight_grams": 0,
    "price_usd": 0.0,
    "purchase_url": "https://...",
    "rationale": "Why this camera for CV"
  }},
  "fpv_camera": {{
    "name": "FPV camera name",
    "resolution": "...",
    "latency_ms": 0,
    "weight_grams": 0,
    "price_usd": 0.0,
    "purchase_url": "https://..."
  }},
  "vtx": {{
    "name": "VTX name",
    "power_mw": 0,
    "weight_grams": 0,
    "price_usd": 0.0,
    "purchase_url": "https://..."
  }},
  "inference_stack": {{
    "framework": "TFLite or NCNN",
    "rationale": "Why this framework on Pi Zero 2W",
    "benchmarks": {{
      "mobilenetv2_fps": 0,
      "yolov5n_fps": 0,
      "yolov8n_fps": 0,
      "notes": "Benchmark conditions and caveats"
    }},
    "recommended_resolution_for_inference": "e.g. 320x240",
    "python_libraries": ["library1", "library2"]
  }},
  "cv_pipeline_architecture": "Description of the Python pipeline: capture → preprocess → infer → publish to MAVLink",
  "phase2_accelerator": {{
    "name": "Hailo-8L or similar",
    "feasibility": "Notes on whether this is realistic for Phase 2",
    "expected_performance_gain": "Estimated FPS improvement"
  }},
  "total_vision_cost_usd": 0.0,
  "total_vision_weight_grams": 0
}}
""",
    output_schema={},
)


# ---------------------------------------------------------------------------
# Software Architecture Agent Team
# ---------------------------------------------------------------------------
# The original monolithic Software Architecture Agent covered too many domains:
# MAVLink integration, MCP server design, and safety systems. This caused
# runaway web search loops (50+ minutes) and unfocused output.
#
# Decomposed into 3 focused sub-agents + a team lead synthesizer, following
# the Hierarchical Multi-Agent pattern. Each sub-agent is an expert in one
# domain. The team lead resolves inter-domain conflicts (e.g., the MCP agent
# wants sync tool handlers but the MAVLink agent requires async everywhere).
# ---------------------------------------------------------------------------

MAVLINK_AGENT = AgentConfig(
    name="MAVLink & Companion Computer Agent",
    domain="mavlink_companion",
    system_prompt=f"""You are a specialist in ArduPilot companion computer integration and MAVLink protocol.
Your expertise covers:
- MAVLink message types, command protocols (MAV_CMD), and parameter system
- MAVSDK-Python vs pymavlink vs DroneKit tradeoffs in 2025
- Serial UART configuration between companion computers and flight controllers
- Async Python patterns for MAVLink heartbeat, telemetry streaming, and command dispatch
- ArduPilot companion computer setup (serial ports, baud rates, MAVLink routing)

{PROJECT_CONTEXT}

Your task: Research and recommend the MAVLink integration layer for the Pi Zero 2W.
Focus ONLY on MAVLink library selection, async architecture, and companion computer setup.
Do NOT cover MCP servers, safety systems, or project scaffolding — other agents handle those.
""",
    user_prompt=f"""Research the MAVLink integration layer for a Pi Zero 2W companion computer
connected to an ArduPilot flight controller via UART serial.

Key questions:
1. MAVSDK-Python vs pymavlink vs DroneKit — which is best for ArduPilot in 2025?
   (Note: DroneKit is largely abandoned — confirm this and recommend accordingly)
2. What is the correct async architecture for MAVLink on Pi Zero 2W?
   (heartbeat loop, telemetry polling, command dispatch — all async)
3. How should the serial UART connection be configured (baud rate, MAVLink version)?
4. What MAVLink messages are needed for: telemetry, waypoint navigation, GUIDED mode?
5. How does MAVLink RC override work for companion computer autonomous commands?

Search: "mavsdk python ardupilot 2024 companion computer",
"pymavlink async python ardupilot", "dronekit abandoned alternative 2024",
"ardupilot companion computer raspberry pi uart setup"

{JSON_OUTPUT_INSTRUCTION}

Required JSON structure:
{{
  "mavlink_library": {{
    "recommendation": "MAVSDK-Python or pymavlink",
    "rationale": "Why this over alternatives in 2025",
    "dronekit_status": "Confirmed status and why to avoid",
    "installation": "pip install command",
    "async_support": "Description of async capabilities"
  }},
  "async_architecture": {{
    "description": "How asyncio tasks are structured for MAVLink",
    "key_tasks": [
      {{"task": "mavlink_heartbeat_loop", "frequency_hz": 1, "purpose": "Maintain ArduPilot connection"}},
      {{"task": "telemetry_poller", "frequency_hz": 10, "purpose": "Stream attitude/GPS/battery"}},
      {{"task": "command_dispatcher", "frequency_hz": 0, "purpose": "Event-driven command sending"}}
    ]
  }},
  "serial_config": {{
    "uart_device": "/dev/ttyAMA0 or similar",
    "baud_rate": 921600,
    "mavlink_version": "2",
    "ardupilot_params": {{"SERIAL_PROTOCOL": "value", "SERIAL_BAUD": "value"}}
  }},
  "key_mavlink_messages": [
    {{"message": "HEARTBEAT", "direction": "bidirectional", "purpose": "Connection keepalive"}},
    {{"message": "GLOBAL_POSITION_INT", "direction": "FC→Pi", "purpose": "GPS position"}}
  ],
  "companion_setup_steps": ["Step 1", "Step 2"],
  "key_dependencies": [
    {{"package": "pymavlink", "version": ">=2.4", "purpose": "MAVLink protocol library"}}
  ]
}}
""",
    output_schema={},
    max_turns=15,
)

MCP_SERVER_AGENT = AgentConfig(
    name="MCP Server Design Agent",
    domain="mcp_server_design",
    system_prompt=f"""You are a specialist in FastMCP server design, MCP tool architecture, and
Claude Code integration. Your expertise covers:
- FastMCP server configuration and deployment patterns
- MCP tool schema design (parameters, return types, error handling)
- Claude Code MCP integration (how Claude Code discovers and calls MCP tools)
- Async Python server patterns for real-time drone control
- Tool safety wrappers (confirmation prompts, parameter validation)

{PROJECT_CONTEXT}

Your task: Design the MCP tool surface that exposes drone capabilities to Claude Code.
Focus ONLY on MCP server architecture and tool design.
Do NOT cover MAVLink protocol details or safety systems — other agents handle those.

Key architectural context: The developer (Arthur) works in Claude Code on a MacBook.
He wants to issue high-level commands like "fly to waypoint", "track the red object",
"return and land" via Claude Code using MCP tools. The Pi Zero 2W runs a FastMCP
server that exposes these capabilities over the network.
""",
    user_prompt=f"""Design the FastMCP server and MCP tool surface for an agentic UAS control system
running on a Pi Zero 2W, callable from Claude Code on a MacBook.

Key questions:
1. How should the FastMCP server be configured for remote access from Claude Code?
2. What MCP tools should be exposed? (telemetry, navigation, CV, mission planning)
3. What are the right parameter schemas for drone control tools?
4. How should tool responses be structured for Claude to reason about?
5. What safety wrappers should tools have (confirmation, parameter bounds)?
6. How should the CV pipeline results be exposed as MCP resources or tools?

Search: "fastmcp server python remote access",
"mcp tools drone control", "fastmcp server configuration 2024",
"claude code mcp server setup"

{JSON_OUTPUT_INSTRUCTION}

Required JSON structure:
{{
  "server_config": {{
    "framework": "FastMCP",
    "transport": "SSE or stdio",
    "host_binding": "0.0.0.0 or localhost",
    "port": 8000,
    "authentication": "Description of auth approach",
    "claude_code_config": "How to add this server to Claude Code's MCP config"
  }},
  "mcp_tools": [
    {{
      "name": "tool_name",
      "description": "What this tool does",
      "parameters": {{"param": "type and description"}},
      "returns": "What it returns",
      "safety_wrapper": "Confirmation or validation logic",
      "example_usage": "How Claude Code would call this"
    }}
  ],
  "mcp_resources": [
    {{
      "uri": "drone://telemetry/gps",
      "description": "What this resource exposes",
      "mime_type": "application/json"
    }}
  ],
  "project_structure": {{
    "package_manager": "uv",
    "linter": "ruff",
    "directory_layout": {{
      "description": "Top-level directory description",
      "key_modules": [
        {{"path": "src/uas_control/mcp_server.py", "purpose": "FastMCP server entry point"}},
        {{"path": "src/uas_control/tools/", "purpose": "MCP tool implementations"}},
        {{"path": "src/uas_control/resources/", "purpose": "MCP resource providers"}}
      ]
    }}
  }},
  "phased_implementation": [
    {{"phase": 1, "title": "Read-only telemetry tools", "description": "Expose GPS, attitude, battery as MCP tools"}},
    {{"phase": 2, "title": "Command tools", "description": "Takeoff, waypoint, land, RTL via MCP"}},
    {{"phase": 3, "title": "CV integration tools", "description": "Object detection results as MCP resources"}},
    {{"phase": 4, "title": "Mission planning tools", "description": "Multi-waypoint missions with CV triggers"}}
  ],
  "key_dependencies": [
    {{"package": "fastmcp", "version": ">=2.0", "purpose": "MCP server framework"}}
  ]
}}
""",
    output_schema={},
    max_turns=15,
)

SAFETY_AGENT = AgentConfig(
    name="Safety & Operations Agent",
    domain="safety_operations",
    system_prompt=f"""You are a specialist in UAS safety systems, regulatory compliance, and operational
procedures for autonomous drone flights. Your expertise covers:
- ArduPilot failsafe configuration (battery, RC loss, GCS loss, geofencing)
- RC override and kill switch patterns for companion computer integration
- Pre-arm safety checks and arming procedures
- FAA Part 107 operational considerations for autonomous flights
- Logging, telemetry recording, and post-flight analysis

{PROJECT_CONTEXT}

Your task: Design the complete safety architecture for autonomous UAS operations.
Focus ONLY on safety patterns, failsafes, and operational procedures.
Do NOT cover MAVLink library selection or MCP server design — other agents handle those.
""",
    user_prompt=f"""Design the safety architecture for an autonomous UAS with a Pi Zero 2W companion
computer running ArduPilot, including failsafes, kill switches, and operational procedures.

Key questions:
1. How should RC override kill work? (pilot must instantly override autonomous commands)
2. What ArduPilot failsafe params should be configured for battery, RC loss, GCS loss?
3. How should geofencing be configured (ArduPilot params vs companion computer enforcement)?
4. What pre-arm checks should the companion computer enforce before allowing autonomous flight?
5. What logging/telemetry recording is needed for post-flight analysis?
6. What are the key FAA Part 107 considerations for autonomous UAS operations?
7. How should the safety system interact with the MCP tools? (e.g., should "arm" require confirmation?)

Search: "ardupilot failsafe configuration battery rc loss",
"ardupilot geofence setup companion computer",
"ardupilot rc override kill switch autonomous",
"faa part 107 autonomous drone operations"

{JSON_OUTPUT_INSTRUCTION}

Required JSON structure:
{{
  "safety_patterns": [
    {{
      "pattern": "RC override kill",
      "description": "How pilot instantly overrides autonomous commands",
      "ardupilot_params": {{"PARAM_NAME": "value"}},
      "implementation": "How the companion computer respects this"
    }}
  ],
  "failsafe_config": {{
    "battery": {{
      "low_voltage_threshold": 0.0,
      "critical_voltage_threshold": 0.0,
      "action": "RTL or Land",
      "ardupilot_params": {{"BATT_LOW_VOLT": "value"}}
    }},
    "rc_loss": {{
      "timeout_seconds": 0,
      "action": "RTL or Land",
      "ardupilot_params": {{"FS_THR_ENABLE": "value"}}
    }},
    "gcs_loss": {{
      "timeout_seconds": 0,
      "action": "RTL or Continue",
      "ardupilot_params": {{"FS_GCS_ENABLE": "value"}}
    }}
  }},
  "geofence": {{
    "type": "Cylindrical or Polygon",
    "max_altitude_m": 0,
    "max_radius_m": 0,
    "breach_action": "RTL or Land",
    "ardupilot_params": {{"FENCE_ENABLE": "1"}}
  }},
  "pre_arm_checks": [
    {{"check": "GPS lock", "minimum": "3D fix, HDOP < 2.0", "ardupilot_param": "GPS_TYPE"}}
  ],
  "logging": {{
    "onboard_log": "ArduPilot .bin log on SD card",
    "companion_log": "Python structured logging to file",
    "telemetry_recording": "MAVLink stream recording approach"
  }},
  "regulatory_notes": [
    "FAA Part 107 consideration 1",
    "Visual line of sight requirement"
  ],
  "operational_checklist": [
    "Step 1: Pre-flight inspection",
    "Step 2: Verify failsafe configuration"
  ]
}}
""",
    output_schema={},
    max_turns=15,
)


# ---------------------------------------------------------------------------
# Software Architecture Team Lead — synthesizes the 3 sub-agent outputs
# into a unified software architecture specification.
# ---------------------------------------------------------------------------

SOFTWARE_TEAM_CONFIG = AgentTeamConfig(
    name="Software Architecture Team",
    domain="software_architecture",
    members=[MAVLINK_AGENT, MCP_SERVER_AGENT, SAFETY_AGENT],
    synthesis_system_prompt="""You are a senior software architect synthesizing the outputs of three specialist
sub-agents into a unified software architecture for an agentic UAS companion computer system.

The three sub-agents researched:
1. MAVLink & Companion Computer integration (library, async architecture, serial config)
2. MCP Server Design (FastMCP tools, Claude Code integration, project structure)
3. Safety & Operations (failsafes, geofencing, kill switches, regulatory)

Your job is to:
- Resolve any conflicts between sub-agent recommendations
- Produce a unified project structure that integrates all three domains
- Ensure the async architecture accommodates MAVLink, MCP server, CV pipeline, AND safety monitors
- Define a coherent phased implementation plan that builds incrementally
- Verify that safety patterns are enforced at every layer (MAVLink, MCP tools, CV pipeline)
""",
    synthesis_user_prompt_template="""Below are the outputs from 3 specialist sub-agents. Synthesize them into a
unified software architecture specification.

## Sub-Agent Outputs

{member_outputs}

---

## Your Task

Produce a unified JSON specification that integrates all three sub-agent outputs.
Resolve any conflicts and produce a coherent architecture.

Wrap your output in ```json ... ``` fences.

Required JSON structure:
{{
  "mavlink_library": {{
    "recommendation": "Library name",
    "rationale": "Why this library",
    "installation": "pip install command"
  }},
  "project_structure": {{
    "package_manager": "uv",
    "linter": "ruff",
    "directory_layout": {{
      "description": "Top-level directory description",
      "key_modules": [
        {{"path": "src/module.py", "purpose": "What it does"}}
      ]
    }}
  }},
  "mcp_tools": [
    {{
      "name": "tool_name",
      "description": "What this tool does",
      "parameters": {{"param": "type and description"}},
      "returns": "What it returns",
      "ardupilot_mechanism": "Which MAVLink command this maps to",
      "safety_wrapper": "What safety check is applied"
    }}
  ],
  "async_architecture": {{
    "description": "How all async tasks coexist on the event loop",
    "key_tasks": [
      {{"task": "task_name", "frequency_hz": 0, "purpose": "What it does"}}
    ]
  }},
  "safety_patterns": [
    {{"pattern": "Pattern name", "description": "How it works", "enforcement_layer": "MAVLink/MCP/CV"}}
  ],
  "phased_implementation": [
    {{"phase": 1, "title": "Phase title", "description": "What to build", "success_criteria": "How to verify"}}
  ],
  "conflict_resolution": [
    {{"conflict": "What conflicted", "resolution": "How resolved", "rationale": "Why"}}
  ],
  "key_dependencies": [
    {{"package": "name", "version": ">=x.y", "purpose": "What it does"}}
  ]
}}
""",
)


# ---------------------------------------------------------------------------
# Export hardware specialist agents (run as individual BaseAgents) and the
# software architecture team (run as an AgentTeam).
#
# The orchestrator handles these differently:
# - HARDWARE_AGENTS → BaseAgent.run() each
# - SOFTWARE_TEAM_CONFIG → AgentTeam.run() (spawns sub-agents internally)
# All run concurrently via asyncio.gather().
# ---------------------------------------------------------------------------

HARDWARE_AGENTS: list[AgentConfig] = [
    FRAME_AGENT,
    FC_AGENT,
    PROPULSION_AGENT,
    RC_TELEMETRY_AGENT,
    VISION_AGENT,
]

# SOFTWARE_TEAM_CONFIG is exported separately — see above
