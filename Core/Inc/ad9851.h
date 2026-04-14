#ifndef __AD9851_H
#define __AD9851_H

#ifdef __cplusplus
extern "C" {
#endif

#include "main.h"
#include <stdint.h>

typedef struct
{
    GPIO_TypeDef *W_CLK_Port;
    uint16_t W_CLK_Pin;

    GPIO_TypeDef *FQ_UD_Port;
    uint16_t FQ_UD_Pin;

    GPIO_TypeDef *DATA_Port;
    uint16_t DATA_Pin;

    GPIO_TypeDef *RESET_Port;
    uint16_t RESET_Pin;

    uint32_t reference_clock_hz;
    uint8_t enable_x6_multiplier;
} AD9851_HandleTypeDef;

void AD9851_Init(AD9851_HandleTypeDef *hdds);
void AD9851_Reset(AD9851_HandleTypeDef *hdds);
void AD9851_SetFrequency(AD9851_HandleTypeDef *hdds, uint32_t frequency_hz);

#ifdef __cplusplus
}
#endif

#endif