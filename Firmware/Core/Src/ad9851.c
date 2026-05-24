#include "ad9851.h"

static void AD9851_WriteBit(AD9851_HandleTypeDef *hdds, uint8_t bit_value)
{
    HAL_GPIO_WritePin(hdds->DATA_Port, hdds->DATA_Pin, bit_value ? GPIO_PIN_SET : GPIO_PIN_RESET);

    HAL_GPIO_WritePin(hdds->W_CLK_Port, hdds->W_CLK_Pin, GPIO_PIN_RESET);
    HAL_GPIO_WritePin(hdds->W_CLK_Port, hdds->W_CLK_Pin, GPIO_PIN_SET);
    HAL_GPIO_WritePin(hdds->W_CLK_Port, hdds->W_CLK_Pin, GPIO_PIN_RESET);
}

static void AD9851_Latch(AD9851_HandleTypeDef *hdds)
{
    HAL_GPIO_WritePin(hdds->FQ_UD_Port, hdds->FQ_UD_Pin, GPIO_PIN_RESET);
    HAL_GPIO_WritePin(hdds->FQ_UD_Port, hdds->FQ_UD_Pin, GPIO_PIN_SET);
    HAL_GPIO_WritePin(hdds->FQ_UD_Port, hdds->FQ_UD_Pin, GPIO_PIN_RESET);
}

static void AD9851_WriteByteLSBFirst(AD9851_HandleTypeDef *hdds, uint8_t value)
{
    uint8_t i;
    for (i = 0; i < 8; i++)
    {
        AD9851_WriteBit(hdds, value & 0x01U);
        value >>= 1;
    }
}

static void AD9851_WriteWord40(AD9851_HandleTypeDef *hdds, uint32_t tuning_word, uint8_t control_byte)
{
    AD9851_WriteByteLSBFirst(hdds, (uint8_t)(tuning_word & 0xFFU));
    AD9851_WriteByteLSBFirst(hdds, (uint8_t)((tuning_word >> 8) & 0xFFU));
    AD9851_WriteByteLSBFirst(hdds, (uint8_t)((tuning_word >> 16) & 0xFFU));
    AD9851_WriteByteLSBFirst(hdds, (uint8_t)((tuning_word >> 24) & 0xFFU));
    AD9851_WriteByteLSBFirst(hdds, control_byte);

    AD9851_Latch(hdds);
}

void AD9851_Reset(AD9851_HandleTypeDef *hdds)
{
    HAL_GPIO_WritePin(hdds->RESET_Port, hdds->RESET_Pin, GPIO_PIN_RESET);
    HAL_GPIO_WritePin(hdds->W_CLK_Port, hdds->W_CLK_Pin, GPIO_PIN_RESET);
    HAL_GPIO_WritePin(hdds->FQ_UD_Port, hdds->FQ_UD_Pin, GPIO_PIN_RESET);
    HAL_GPIO_WritePin(hdds->DATA_Port, hdds->DATA_Pin, GPIO_PIN_RESET);

    HAL_Delay(1);

    HAL_GPIO_WritePin(hdds->RESET_Port, hdds->RESET_Pin, GPIO_PIN_SET);
    HAL_Delay(1);
    HAL_GPIO_WritePin(hdds->RESET_Port, hdds->RESET_Pin, GPIO_PIN_RESET);

    HAL_GPIO_WritePin(hdds->W_CLK_Port, hdds->W_CLK_Pin, GPIO_PIN_SET);
    HAL_GPIO_WritePin(hdds->W_CLK_Port, hdds->W_CLK_Pin, GPIO_PIN_RESET);

    HAL_GPIO_WritePin(hdds->FQ_UD_Port, hdds->FQ_UD_Pin, GPIO_PIN_SET);
    HAL_GPIO_WritePin(hdds->FQ_UD_Port, hdds->FQ_UD_Pin, GPIO_PIN_RESET);
}

void AD9851_Init(AD9851_HandleTypeDef *hdds)
{
    AD9851_Reset(hdds);
    AD9851_SetFrequency(hdds, 1000000U);
}

void AD9851_SetFrequency(AD9851_HandleTypeDef *hdds, uint32_t frequency_hz)
{
    uint32_t system_clock_hz;
    uint64_t numerator;
    uint32_t tuning_word;
    uint8_t control_byte;

    system_clock_hz = hdds->reference_clock_hz;

    if (hdds->enable_x6_multiplier != 0U)
    {
        system_clock_hz = system_clock_hz * 6U;
        control_byte = 0x01U;
    }
    else
    {
        control_byte = 0x00U;
    }

    numerator = ((uint64_t)frequency_hz << 32);
    tuning_word = (uint32_t)(numerator / system_clock_hz);

    AD9851_WriteWord40(hdds, tuning_word, control_byte);
}