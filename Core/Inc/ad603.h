#ifndef __AD603_H
#define __AD603_H

#ifdef __cplusplus
extern "C" {
#endif

#include "main.h"
#include <stdint.h>

/* =====================================================================
 *  AD603 dual-cascaded VGA driver (Taidacent module).
 *
 *  ============================  SAFETY  ===============================
 *  The AD603 control voltage MUST NEVER exceed 1.0 V. Above ~1.2 V the
 *  device self-oscillates, sending uncontrolled energy through the
 *  LM7171 driver -> power amplifier -> step-up transformer -> 1.5 kV
 *  electrodes. Every voltage path in this driver is hard-clamped to
 *  AD603_MAX_VCTL_V, and every DAC code path is hard-clamped to
 *  AD603_DAC_MAX_SAFE_CODE, regardless of what the caller passes.
 *
 *  AD603_Init() always leaves the device muted (Vctl = 0 V, minimum
 *  cascaded gain). Boot order in main.c MUST init the AD603 BEFORE the
 *  AD9851 is enabled, so the VGA is muted by the time RF appears at
 *  its input.
 *  ===================================================================== */

/* Hard safety limits */
#define AD603_MAX_VCTL_V          (1.0f)
#define AD603_MIN_VCTL_V          (0.0f)

/* DAC reference and resolution (STM32H7 internal DAC, VREF = VDDA = 3.3 V) */
#define AD603_VREF_V              (3.3f)
#define AD603_DAC_MAX_CODE        (4095U)   /* 12-bit, right-aligned */
/* Largest DAC code that still produces <= 1.0 V on the output. */
#define AD603_DAC_MAX_SAFE_CODE   ((uint32_t)((AD603_MAX_VCTL_V / AD603_VREF_V) \
                                              * (float)AD603_DAC_MAX_CODE))   /* ~1241 */

/* Default cascaded transfer (per Taidacent datasheet): 0 V -> 0 dB, 1 V -> 80 dB. */
#define AD603_DEFAULT_DB_PER_V    (80.0f)
#define AD603_DEFAULT_DB_AT_0V    (0.0f)
#define AD603_MIN_GAIN_DB         (AD603_DEFAULT_DB_AT_0V)
#define AD603_MAX_GAIN_DB         (AD603_DEFAULT_DB_AT_0V + \
                                   AD603_DEFAULT_DB_PER_V * AD603_MAX_VCTL_V)

typedef struct
{
    /* Hardware binding (caller-supplied) */
    DAC_TypeDef *dac;            /* e.g. DAC1                                   */
    uint32_t     channel;        /* 1 or 2 (DAC1_OUT1 = PA4, DAC1_OUT2 = PA5)   */

    /* Calibration: gain_db = slope_db_per_v * Vctl + offset_db.
       Init() seeds these with the default cascaded transfer if zero.   */
    float        slope_db_per_v;
    float        offset_db;

    /* Last applied state (read-back, written by every set call) */
    float        last_vctl_v;
    float        last_gain_db;

    uint8_t      initialised;
} AD603_HandleTypeDef;

HAL_StatusTypeDef AD603_Init(AD603_HandleTypeDef *h);
HAL_StatusTypeDef AD603_Mute(AD603_HandleTypeDef *h);
HAL_StatusTypeDef AD603_SetControlVoltage(AD603_HandleTypeDef *h, float volts);
HAL_StatusTypeDef AD603_SetGainDb(AD603_HandleTypeDef *h, float gain_db);
HAL_StatusTypeDef AD603_SetLinearGain(AD603_HandleTypeDef *h, float gain_vv);
HAL_StatusTypeDef AD603_Calibrate(AD603_HandleTypeDef *h,
                                  float v1, float db1,
                                  float v2, float db2);

float AD603_GetGainDb(const AD603_HandleTypeDef *h);
float AD603_GetControlVoltage(const AD603_HandleTypeDef *h);

#ifdef __cplusplus
}
#endif

#endif /* __AD603_H */
