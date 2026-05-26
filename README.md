# Custom RF Generator for Quadropole Ion Guides

This repository contains the design, firmware, and documentation for a custom computer-controlled RF generator capable of driving ~1 kV waveforms for charge detection mass spectrometry. 

Details regarding the overall design architecture and integration can be found in the [RF Gen Final Deliverable.pptx](./RF%20Gen%20Final%20Deliverable.pptx). Further detail of each system component can be found in their respective folders.

## Repository Structure

rfgenerator/
├── Firmware/                       # Application firmware and STM32 build configuration
├── PCB/                            # PA107 Power Amplifier design files and BOM
├── Sims/                           # Simulation files for power amp verification
├── Transformer/                    # Custom transformer research, winding specs, and lab notes
├── RF Gen Final Deliverable.pptx   # Final presentation outlining the Spring 2026 project scope and overall design architecture
└── [SOW] Physical Chemistry RF and Array.docx.pdf