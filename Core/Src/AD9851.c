#include "AD9851.h"
#include "stm32h7xx_hal.h"

// Internal function to send serial data to AD9851
static void AD9851_SerialWrite(uint8_t data) {
    for (int i = 0; i < 8; i++) {
        // Set DATA pin
        if (data & 0x01) {
            HAL_GPIO_WritePin(AD9851_DATA_PORT, AD9851_DATA_PIN, GPIO_PIN_SET);
        } else {
            HAL_GPIO_WritePin(AD9851_DATA_PORT, AD9851_DATA_PIN, GPIO_PIN_RESET);
        }
        data >>= 1;

        // Pulse W_CLK
        HAL_GPIO_WritePin(AD9851_W_CLK_PORT, AD9851_W_CLK_PIN, GPIO_PIN_SET);
        HAL_Delay(1); // Small delay for timing
        HAL_GPIO_WritePin(AD9851_W_CLK_PORT, AD9851_W_CLK_PIN, GPIO_PIN_RESET);
        HAL_Delay(1);
    }
}

// Initialize AD9851 interface pins
void AD9851_Init(void) {
    GPIO_InitTypeDef GPIO_InitStruct = {0};

    // Enable GPIO clocks
    AD9851_W_CLK_CLK_ENABLE();
    AD9851_DATA_CLK_ENABLE();
    AD9851_FU_UD_CLK_ENABLE();
    AD9851_RESET_CLK_ENABLE();

    // Configure W_CLK pin as output
    GPIO_InitStruct.Pin = AD9851_W_CLK_PIN;
    GPIO_InitStruct.Mode = GPIO_MODE_OUTPUT_PP;
    GPIO_InitStruct.Pull = GPIO_NOPULL;
    GPIO_InitStruct.Speed = GPIO_SPEED_FREQ_LOW;
    HAL_GPIO_Init(AD9851_W_CLK_PORT, &GPIO_InitStruct);

    // Configure DATA pin as output
    GPIO_InitStruct.Pin = AD9851_DATA_PIN;
    HAL_GPIO_Init(AD9851_DATA_PORT, &GPIO_InitStruct);

    // Configure FU_UD pin as output
    GPIO_InitStruct.Pin = AD9851_FU_UD_PIN;
    HAL_GPIO_Init(AD9851_FU_UD_PORT, &GPIO_InitStruct);

    // Configure RESET pin as output
    GPIO_InitStruct.Pin = AD9851_RESET_PIN;
    HAL_GPIO_Init(AD9851_RESET_PORT, &GPIO_InitStruct);

    // Initialize all pins to low
    HAL_GPIO_WritePin(AD9851_W_CLK_PORT, AD9851_W_CLK_PIN, GPIO_PIN_RESET);
    HAL_GPIO_WritePin(AD9851_DATA_PORT, AD9851_DATA_PIN, GPIO_PIN_RESET);
    HAL_GPIO_WritePin(AD9851_FU_UD_PORT, AD9851_FU_UD_PIN, GPIO_PIN_RESET);
    HAL_GPIO_WritePin(AD9851_RESET_PORT, AD9851_RESET_PIN, GPIO_PIN_RESET);

    // Reset the AD9851
    AD9851_Reset();
}

// Reset the AD9851
void AD9851_Reset(void) {
    HAL_GPIO_WritePin(AD9851_RESET_PORT, AD9851_RESET_PIN, GPIO_PIN_SET);
    HAL_Delay(1); // Minimum 5 ns, but HAL_Delay is in ms
    HAL_GPIO_WritePin(AD9851_RESET_PORT, AD9851_RESET_PIN, GPIO_PIN_RESET);
    HAL_Delay(1);
}

// Set the output frequency
void AD9851_SetFrequency(uint32_t frequency_hz) {
    if (frequency_hz > AD9851_MAX_FREQUENCY) {
        frequency_hz = AD9851_MAX_FREQUENCY;
    }

    // Calculate frequency tuning word
    // FTW = (frequency * 2^32) / clock_frequency
    uint64_t ftw = ((uint64_t)frequency_hz << 32) / AD9851_CLOCK_FREQUENCY;

    // Send 32-bit frequency word + 8-bit control (0x00 for default)
    AD9851_WriteData((uint32_t)ftw, 0x00);
}

// Set the phase (0-360 degrees)
void AD9851_SetPhase(uint16_t phase_degrees) {
    // Phase tuning word: 5 bits for 11.25 degree resolution
    uint8_t phase_word = (phase_degrees * 32) / 360;

    // For phase adjustment, we need to modify the control byte
    // This is a simplified implementation - in practice, you'd combine with frequency
    AD9851_WriteData(0, phase_word << 3); // Shift to phase bits in control word
}

// Write data to AD9851 (serial mode)
void AD9851_WriteData(uint32_t frequency_word, uint8_t control_bits) {
    // Send 32-bit frequency word LSB first
    AD9851_SerialWrite(frequency_word & 0xFF);
    AD9851_SerialWrite((frequency_word >> 8) & 0xFF);
    AD9851_SerialWrite((frequency_word >> 16) & 0xFF);
    AD9851_SerialWrite((frequency_word >> 24) & 0xFF);

    // Send 8-bit control word
    AD9851_SerialWrite(control_bits);

    // Pulse FU_UD to latch the data
    AD9851_Update();
}

// Update/latch the data
void AD9851_Update(void) {
    HAL_GPIO_WritePin(AD9851_FU_UD_PORT, AD9851_FU_UD_PIN, GPIO_PIN_SET);
    HAL_Delay(1); // Minimum 7 ns
    HAL_GPIO_WritePin(AD9851_FU_UD_PORT, AD9851_FU_UD_PIN, GPIO_PIN_RESET);
    HAL_Delay(1);
}