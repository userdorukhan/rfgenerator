# PA107 Power Amplifier PCB

This PCB serves as the primary RF amplifier stage for the charge detection mass spectrometer. It takes a low-voltage signal from the external DDS, conditions it, and amplifies it to a large output swing for the off-board step-up transformer.

## Signal Flow

```
DDS output -> AD603 VGA -> LM7171 pre-amp (x10) -> PA107 power stage (x20) -> output snubber -> transformer
```

The 1 Vpp DDS sine wave enters the AD603 variable-gain amplifier whose gain is set by an STM32 DAC pin. It then enters the LM7171 op-amp at gain 10 and a PA107 power stage at gain 20, for a fixed gain of 200 after the adjustable front end. The PA107 output passes through an output snubber to the transformer connector.

## Signal Levels and Bandwidth

The system gain spans roughly +35 dB to +77 dB, so the front end can place the output anywhere from about 56 Vpp at minimum gain up to 180 Vpp (max output swing of PA107). 

The bandwidth is ~2MHz, limited by the PA107’s slew-rate limit at its max output swing.

Note: In practice, the output is rail-limited rather than gain-limited. The PA107 saturates near its high-voltage rails (around 180 Vpp at the ±100-150 V rails), which is reached well below the top of the VGA range, so only the lower portion of the gain range is usable before the power stage clips.

## Design Choices

- Adjustable front end. The AD603 lets the lab trim overall gain at runtime without changing components.
- Two-stage fixed amplification. Splitting the fixed gain between the LM7171 and PA107 keeps each stage within a comfortable bandwidth and swing range rather than asking a single stage for the full gain.
- Off-board transformer. The step-up transformer connects through a dedicated output connector, keeping the high-voltage secondary off the amplifier board.
- Separate supply domains. The PA107 high-voltage rails, the ±15V bias/boost rails, and the ±5V front-end rails are kept distinct, each with its own decoupling and bulk capacitance.

## Safety and Protection

- Input clamp on the power-stage input to keep it within the bias rails.
- Output snubber (series resistor and capacitor) to damp ringing into the cable and transformer.
- Rail flyback diodes on the high-voltage supply.
- Bleeder resistors to discharge the high-voltage rails when power is removed.

## Left to Implement or Tune

- The current resistor and capacitor are a starting point. Final values should be set during bring-up against the actual cable and transformer load.
- No feedback compensation capacitor is fitted. Stability at gain 20 into the cable and transformer load should be confirmed, and a compensation cap added if needed.
- Confirm actual output swing on the tied high-voltage rails before deciding whether to separate them.

## Application Notes

Akshay and Carolyn may continue developing this board to bring the STM32 controller and DDS chip on-board, turning the current multi-board setup into a single integrated module. The existing header interface already defines the signals that would migrate on-board.

We are also willing to fabricate the board and carry out bring-up in the Fall.
