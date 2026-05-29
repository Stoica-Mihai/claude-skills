# Re: smoke test for your STM32 board

I have to decline on this one — what you're describing is a **hardware power-on self-test (POST / bring-up check)**, not the kind of "smoke test" my smoke-test skill is built for.

The terminology overlap is real and the original metaphor is yours, not mine: in electrical engineering, a smoke test literally meant *apply power and watch for smoke*. The software industry borrowed the name for a build-verification suite — a fast, broad, shallow check that a fresh build is stable enough to bother testing further. That software meaning is what my templates and scaffolding cover (FastAPI/pytest, Express/vitest, Go net/http, axum/tower). None of them apply to your STM32.

Specifically, my skill cannot help you with:

- Toggling a GPIO and reading the LED state back (needs board firmware + a debug probe, or a host-side logic analyzer)
- UART loopback / `AT`-style ping over a serial port (needs a host script talking to `/dev/ttyUSBx` at the right baud, plus the MCU-side echo handler)
- I2C bus liveness — scanning addresses 0x03..0x77 for ACKs (needs an I2C master on the MCU or a host-side bus pirate / FT232H)
- Rail voltage / current sanity checks (needs a bench PSU with current limit, or an INA219/INA260 on the rail)

Those checks live in firmware (an init-time self-test in `main()` before the application starts), or in a host-side bring-up harness (Python + `pyserial` + `smbus2`, or a vendor tool like STM32CubeProgrammer / OpenOCD scripts). That is a different discipline from CI build-verification, and I would be making things up if I produced a pytest scaffold for it.

## What I would suggest instead

If you want to drive this forward, the typical shape of an STM32 power-on self-test is:

1. **Firmware-side POST**, run once in `main()` before the scheduler / main loop:
   - Read RCC reset cause register, log it over UART
   - Blink LED N times at a known cadence (visible "I booted" signal)
   - `printf` a banner over UART at the project's standard baud (115200 is common) — gives you the "UART responds" check for free
   - Run an I2C bus scan (or just probe the expected sensor addresses) and log ACK/NACK
   - Optionally read MCU internal temp sensor + VREFINT for a rough rail-sanity proxy

2. **Host-side bring-up script** that sits on the other end of the UART and asserts the banner appears, the bus-scan line lists the expected addresses, and the blink rate looks right (a photodiode or just a human eyeballing it for first-article boards).

Vendor reference: ST's `STM32CubeMX` generates HAL skeletons for all three peripherals (GPIO/USART/I2C); `HAL_I2C_IsDeviceReady` is the canonical bus-scan primitive.

If you want, I can help you draft that firmware POST routine or the host-side `pyserial` harness directly — just say the word and I'll switch hats. But it won't come out of the smoke-test skill; it'll be hand-written embedded C and a small Python script.
