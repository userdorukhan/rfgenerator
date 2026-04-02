#pragma once
#include "main.h"

// Serial Interface Pins (primary for AD9851 control)
#define AD9851_W_CLK_PIN       GPIO_PIN_4    // PA4 (D4 on Arduino header)
#define AD9851_W_CLK_PORT      GPIOA
#define AD9851_W_CLK_CLK_ENABLE()  __HAL_RCC_GPIOA_CLK_ENABLE()

#define AD9851_DATA_PIN        GPIO_PIN_5    // PA5 (D5 on Arduino header) 
#define AD9851_DATA_PORT       GPIOA
#define AD9851_DATA_CLK_ENABLE()   __HAL_RCC_GPIOA_CLK_ENABLE()

#define AD9851_FU_UD_PIN       GPIO_PIN_10   // PB10 (D6 on Arduino header)
#define AD9851_FU_UD_PORT      GPIOB
#define AD9851_FU_UD_CLK_ENABLE()  __HAL_RCC_GPIOB_CLK_ENABLE()

#define AD9851_RESET_PIN       GPIO_PIN_8    // PA8 (D7 on Arduino header)
#define AD9851_RESET_PORT      GPIOA
#define AD9851_RESET_CLK_ENABLE()  __HAL_RCC_GPIOA_CLK_ENABLE()

// AD9851 Constants
#define AD9851_CLOCK_FREQUENCY 125000000UL  // 125 MHz reference clock (typical for AD9851)
#define AD9851_MAX_FREQUENCY   40000000UL   // 40 MHz max output frequency

// Function Prototypes
void AD9851_Init(void);
void AD9851_Reset(void);
void AD9851_SetFrequency(uint32_t frequency_hz);
void AD9851_SetPhase(uint16_t phase_degrees);
void AD9851_WriteData(uint32_t frequency_word, uint8_t control_bits);
void AD9851_Update(void);

