#include "ad603.h"
#include <math.h>

/* =====================================================================
 *  AD603 driver — direct DAC register access (no HAL DAC dependency).
 *
 *  EVERY voltage path is hard-clamped to AD603_MAX_VCTL_V (1.0 V) and
 *  EVERY DAC code path is hard-clamped to AD603_DAC_MAX_SAFE_CODE
 *  (~1241/4095). This is the last line of defense for the AD603 and
 *  the high-voltage stages downstream — do not weaken these clamps.
 * ===================================================================== */

static uint32_t volts_to_dac_code(float v)
{
    if (v < AD603_MIN_VCTL_V) v = AD603_MIN_VCTL_V;
    if (v > AD603_MAX_VCTL_V) v = AD603_MAX_VCTL_V;          /* HARD CLAMP */

    float code_f = (v / AD603_VREF_V) * (float)AD603_DAC_MAX_CODE;
    uint32_t code = (uint32_t)(code_f + 0.5f);
    if (code > AD603_DAC_MAX_SAFE_CODE) {
        code = AD603_DAC_MAX_SAFE_CODE;                      /* belt + suspenders */
    }
    return code;
}

static void dac_write(AD603_HandleTypeDef *h, uint32_t code)
{
    if (h->channel == 1U) {
        h->dac->DHR12R1 = code;
    } else {
        h->dac->DHR12R2 = code;
    }
}

HAL_StatusTypeDef AD603_Init(AD603_HandleTypeDef *h)
{
    if (h == NULL || h->dac == NULL) return HAL_ERROR;
    if (h->channel != 1U && h->channel != 2U) return HAL_ERROR;

    /* Seed default calibration if caller left it zero. */
    if (h->slope_db_per_v == 0.0f) {
        h->slope_db_per_v = AD603_DEFAULT_DB_PER_V;
    }
    /* offset_db can legitimately be 0 — no default needed. */

    /* Enable DAC12 peripheral clock (APB1L). Idempotent. */
    RCC->APB1LENR |= RCC_APB1LENR_DAC12EN;
    __DSB();

    /* Configure GPIO as analog. PA4 = DAC1_OUT1, PA5 = DAC1_OUT2. */
    if (h->dac == DAC1) {
        __HAL_RCC_GPIOA_CLK_ENABLE();
        uint32_t pin = (h->channel == 1U) ? 4U : 5U;
        GPIOA->MODER |= (0x3UL << (pin * 2U));               /* analog mode */
    }

    /* SAFETY ORDER: write 0 V to the data register BEFORE enabling the
       channel, so the very first sample on the pin is 0 V (mute). */
    dac_write(h, 0U);

    if (h->channel == 1U) {
        h->dac->CR &= ~(DAC_CR_TEN1 | DAC_CR_EN1);           /* clean slate    */
        /* MCR MODE1 default (0) = external pin, output buffer enabled.       */
        h->dac->CR |= DAC_CR_EN1;                            /* software trig  */
    } else {
        h->dac->CR &= ~(DAC_CR_TEN2 | DAC_CR_EN2);
        h->dac->CR |= DAC_CR_EN2;
    }

    h->last_vctl_v   = 0.0f;
    h->last_gain_db  = h->offset_db;
    h->initialised   = 1U;
    return HAL_OK;
}

HAL_StatusTypeDef AD603_Mute(AD603_HandleTypeDef *h)
{
    if (h == NULL || !h->initialised) return HAL_ERROR;
    dac_write(h, 0U);
    h->last_vctl_v  = 0.0f;
    h->last_gain_db = h->offset_db;
    return HAL_OK;
}

HAL_StatusTypeDef AD603_SetControlVoltage(AD603_HandleTypeDef *h, float volts)
{
    if (h == NULL || !h->initialised) return HAL_ERROR;

    if (volts < AD603_MIN_VCTL_V) volts = AD603_MIN_VCTL_V;
    if (volts > AD603_MAX_VCTL_V) volts = AD603_MAX_VCTL_V;  /* HARD CLAMP */

    dac_write(h, volts_to_dac_code(volts));
    h->last_vctl_v  = volts;
    h->last_gain_db = h->slope_db_per_v * volts + h->offset_db;
    return HAL_OK;
}

HAL_StatusTypeDef AD603_SetGainDb(AD603_HandleTypeDef *h, float gain_db)
{
    if (h == NULL || !h->initialised) return HAL_ERROR;
    if (h->slope_db_per_v <= 0.0f) return HAL_ERROR;         /* invalid cal   */

    /* Solve for Vctl, then let SetControlVoltage handle the clamp. */
    float volts = (gain_db - h->offset_db) / h->slope_db_per_v;
    return AD603_SetControlVoltage(h, volts);
}

HAL_StatusTypeDef AD603_SetLinearGain(AD603_HandleTypeDef *h, float gain_vv)
{
    if (h == NULL || !h->initialised) return HAL_ERROR;
    if (gain_vv <= 0.0f) {
        return AD603_Mute(h);
    }
    float gain_db = 20.0f * log10f(gain_vv);
    return AD603_SetGainDb(h, gain_db);
}

HAL_StatusTypeDef AD603_Calibrate(AD603_HandleTypeDef *h,
                                  float v1, float db1,
                                  float v2, float db2)
{
    if (h == NULL) return HAL_ERROR;
    if (v1 == v2) return HAL_ERROR;                          /* div-by-zero   */
    if (v1 < AD603_MIN_VCTL_V || v2 < AD603_MIN_VCTL_V) return HAL_ERROR;
    if (v1 > AD603_MAX_VCTL_V || v2 > AD603_MAX_VCTL_V) return HAL_ERROR;

    float slope = (db2 - db1) / (v2 - v1);
    if (slope <= 0.0f) return HAL_ERROR;                     /* sign sanity   */

    h->slope_db_per_v = slope;
    h->offset_db      = db1 - slope * v1;
    return HAL_OK;
}

float AD603_GetGainDb(const AD603_HandleTypeDef *h)
{
    return (h != NULL) ? h->last_gain_db : 0.0f;
}

float AD603_GetControlVoltage(const AD603_HandleTypeDef *h)
{
    return (h != NULL) ? h->last_vctl_v : 0.0f;
}
