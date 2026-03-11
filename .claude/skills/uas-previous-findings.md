---
name: uas-previous-findings
description: Summary of V1 research findings and known issues to inform V2 research
---

# V1 Research Findings Summary

A multi-agent research system (6 agents + synthesis) produced the V1 report at `output/uas_build_report.md`. Key findings to build upon (not blindly accept):

## V1 Hardware Recommendations
- **Frame:** Lumenier QAV-S 2 (3", 55g, $78) — chosen for weight, but limits payload
- **FC:** Matek H743-MINI V3 (20x20, 6g, $56) — H7 processor, 5.5 UARTs, dual IMUs
- **Motors:** BETAFPV 1505 3600KV ($60/4) — originally spec'd for 4" props (CONFLICT)
- **ESC:** Holybro Tekko32 F4 4in1 45A ($50) — separate from FC
- **Props:** HQ 3025 (corrected from 4" to 3" in synthesis)
- **Battery:** GNB 650mAh 4S 80C ($15 each)
- **GPS:** Matek M10-5883 GPS/Compass ($35)
- **RC TX:** RadioMaster Pocket ELRS ($50)
- **RC RX:** BETAFPV ELRS Nano 2.4GHz ($10)
- **Telemetry:** Holybro SiK V3 915MHz ($65/pair)
- **Companion Computer:** Pi Zero 2W (OWNED, $0) — KNOWN BOTTLENECK (2-5 FPS CV)
- **CV Camera:** Pi Camera Module 3 ($25)
- **FPV Camera:** Caddx Ant Lite ($16) + Rush Tiny Tank VTX ($30)
- **FPV Goggles:** Eachine EV800D ($90) — REMOVED in V2

**V1 Total:** $817.62 | **V1 AUW:** 333g

## V1 Conflicts Resolved
1. FC selection: H743-MINI V3 chosen over SpeedyBee F405 AIO (ArduPilot support, UARTs, dual IMU)
2. Prop size: Corrected from 4" to 3" to match frame
3. Battery: 650mAh confirmed over 850mAh (weight trade)
4. Pi power: Separate UBEC recommended over FC BEC tap
5. Sub-250g: Confirmed impossible with full sensor suite — accepted
6. Software output: Truncated/malformed JSON from sub-agents

## V1 Known Issues (Must Address in V2)
- Pi Zero 2W limits CV to 2-5 FPS — NOT production-ready
- Vision Agent reported Pi weight as 10g (actual: 31g)
- All 3 software sub-agents hit max_turns without producing complete JSON
- Analog FPV system now replaced by digital FPV + device streaming
- No SITL/simulation planning in V1 phased build

## V1 Strengths to Preserve
- UART allocation map (Section 4) — thorough and correct
- Wiring diagram (Section 5) — comprehensive text-based schematic
- Safety architecture (Section 7) — defense-in-depth layering
- ArduPilot parameter configs — well-documented with rationale
- Conflict resolution methodology — explicit tradeoff documentation
