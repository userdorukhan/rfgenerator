/* USER CODE BEGIN Header */
/**
  ******************************************************************************
  * @file           : main.c
  * @brief          : Main program body
  ******************************************************************************
  * @attention
  *
  * Copyright (c) 2026 STMicroelectronics.
  * All rights reserved.
  *
  * This software is licensed under terms that can be found in the LICENSE file
  * in the root directory of this software component.
  * If no LICENSE file comes with this software, it is provided AS-IS.
  *
  ******************************************************************************
  */
/* USER CODE END Header */
/* Includes ------------------------------------------------------------------*/
#include "main.h"
#include <stdlib.h>
#include <string.h>

/* Private includes ----------------------------------------------------------*/
/* USER CODE BEGIN Includes */
#include "ad9851.h"
#include "ad603.h"
/* USER CODE END Includes */

/* Private typedef -----------------------------------------------------------*/
/* USER CODE BEGIN PTD */

/* USER CODE END PTD */

/* Private define ------------------------------------------------------------*/
/* USER CODE BEGIN PD */
#define DDS_MIN_FREQUENCY_HZ        (0UL)
#define DDS_MAX_FREQUENCY_HZ        (10000000UL)
#define DDS_COMMAND_BUFFER_SIZE     (48U)
#define DDS_COMMAND_IDLE_TIMEOUT_MS (250UL)
/* USER CODE END PD */

/* Private macro -------------------------------------------------------------*/
/* USER CODE BEGIN PM */

/* USER CODE END PM */

/* Private variables ---------------------------------------------------------*/

COM_InitTypeDef BspCOMInit;

/* USER CODE BEGIN PV */
AD9851_HandleTypeDef hdds;
AD603_HandleTypeDef  hvga;
static volatile uint32_t dds_requested_frequency_hz = 7700000UL;
static uint32_t dds_active_frequency_hz = 0UL;
static char dds_command_buffer[DDS_COMMAND_BUFFER_SIZE];
static uint32_t dds_command_length = 0UL;
static volatile uint8_t dds_command_ready = 0U;
static volatile uint8_t dds_command_overflow = 0U;
static uint8_t dds_console_rx_byte = 0U;
static uint32_t dds_last_command_byte_tick = 0UL;
/* USER CODE END PV */

/* Private function prototypes -----------------------------------------------*/
void SystemClock_Config(void);
static void MPU_Config(void);
static void MX_GPIO_Init(void);
/* USER CODE BEGIN PFP */
static void DDS_ApplyFrequency(void);
static void Console_StartRx(void);
static void Console_ProcessCommand(void);
static void Sweep_Run(float db_start, float db_end, float db_step, uint32_t step_ms);
/* USER CODE END PFP */

/* Private user code ---------------------------------------------------------*/
/* USER CODE BEGIN 0 */

/* USER CODE END 0 */

/**
  * @brief  The application entry point.
  * @retval int
  */
int main(void)
{

  /* USER CODE BEGIN 1 */

  /* USER CODE END 1 */

  /* MPU Configuration--------------------------------------------------------*/
  MPU_Config();

  /* MCU Configuration--------------------------------------------------------*/

  /* Reset of all peripherals, Initializes the Flash interface and the Systick. */
  HAL_Init();

  /* USER CODE BEGIN Init */

  /* USER CODE END Init */

  /* Configure the system clock */
  SystemClock_Config();

  /* USER CODE BEGIN SysInit */

  /* USER CODE END SysInit */

  /* Initialize all configured peripherals */
  MX_GPIO_Init();
  /* USER CODE BEGIN 2 */
  /* ============================================================
   *  SAFETY-CRITICAL BOOT ORDER
   *  Step 1: bring up the AD603 VGA in its muted state (Vctl=0V)
   *          BEFORE any RF appears at its input.
   *  Step 2: only then enable the AD9851 DDS.
   *  If we reverse this, the AD603 may briefly sit at full gain
   *  while RF arrives, slamming the LM7171/PA/transformer.
   * ============================================================ */
  hvga.dac     = DAC1;
  hvga.channel = 1U;            /* DAC1_OUT1 -> PA4 -> AD603 DA-input */
  hvga.slope_db_per_v = 0.0f;   /* Init() seeds defaults if zero      */
  hvga.offset_db      = 0.0f;
  if (AD603_Init(&hvga) != HAL_OK)
  {
    Error_Handler();
  }

  hdds.W_CLK_Port = AD9851_W_CLK_GPIO_Port;
  hdds.W_CLK_Pin = AD9851_W_CLK_Pin;

  hdds.FQ_UD_Port = AD9851_FQ_UD_GPIO_Port;
  hdds.FQ_UD_Pin = AD9851_FQ_UD_Pin;

  hdds.DATA_Port = AD9851_DATA_GPIO_Port;
  hdds.DATA_Pin = AD9851_DATA_Pin;

  hdds.RESET_Port = AD9851_RESET_GPIO_Port;
  hdds.RESET_Pin = AD9851_RESET_Pin;

  hdds.reference_clock_hz = 30000000U;
  hdds.enable_x6_multiplier = 1U;

  AD9851_Init(&hdds);            /* AD603 already muted — RF safe to enable */
  HAL_Delay(10);

  /* Initialize COM1 port (115200, 8 bits (7-bit data + 1 stop bit), no parity */
  BspCOMInit.BaudRate   = 115200;
  BspCOMInit.WordLength = COM_WORDLENGTH_8B;
  BspCOMInit.StopBits   = COM_STOPBITS_1;
  BspCOMInit.Parity     = COM_PARITY_NONE;
  BspCOMInit.HwFlowCtl  = COM_HWCONTROL_NONE;
  if (BSP_COM_Init(COM1, &BspCOMInit) != BSP_ERROR_NONE)
  {
    Error_Handler();
  }
  /* Enable USART3 interrupt in NVIC so HAL_UART_Receive_IT callbacks fire */
  HAL_NVIC_SetPriority(USART3_IRQn, 5, 0);
  HAL_NVIC_EnableIRQ(USART3_IRQn);
#if (USE_COM_LOG > 0)
  BSP_COM_SelectLogPort(COM1);
#endif

  printf("\r\nRF generator console ready. AD603 muted at boot.\r\n");
  printf("Frequency : '<num>[ Hz|kHz|MHz]'   e.g. 7.7 MHz\r\n");
  printf("Gain      : 'gain <dB>'  /  'vctl <volts>'  /  'mute'\r\n");
  printf("Sweep     : 'sweep'   (0->80 dB, 5 dB steps, 200 ms each)\r\n");
  printf("Calibrate : 'cal <v1> <db1> <v2> <db2>'   (RAM only)\r\n");
  printf("Status    : 'status'\r\n");
  Console_StartRx();
  DDS_ApplyFrequency();
  /* USER CODE END 2 */

  /* Initialize leds */
  BSP_LED_Init(LED_GREEN);
  BSP_LED_Init(LED_YELLOW);
  BSP_LED_Init(LED_RED);

  /* Initialize USER push-button, will be used to trigger an interrupt each time it's pressed.*/
  BSP_PB_Init(BUTTON_USER, BUTTON_MODE_EXTI);

  /* Infinite loop */
  /* USER CODE BEGIN WHILE */
  while (1)
  {

    /* USER CODE END WHILE */

    /* USER CODE BEGIN 3 */
    if (dds_command_overflow != 0U)
    {
      dds_command_overflow = 0U;
      printf("\r\n[DDS] Command too long. Clearing buffer.\r\n");
    }

    if (dds_command_ready != 0U)
    {
      Console_ProcessCommand();
    }
    else if ((dds_command_length > 0U) &&
             ((HAL_GetTick() - dds_last_command_byte_tick) >= DDS_COMMAND_IDLE_TIMEOUT_MS))
    {
      dds_command_ready = 1U;
      Console_ProcessCommand();
    }

    if (dds_active_frequency_hz != dds_requested_frequency_hz)
    {
      DDS_ApplyFrequency();
    }

    BSP_LED_Toggle(LED_GREEN);
    HAL_Delay(500);
  }
  /* USER CODE END 3 */
}

/**
  * @brief System Clock Configuration
  * @retval None
  */
void SystemClock_Config(void)
{
  RCC_OscInitTypeDef RCC_OscInitStruct = {0};
  RCC_ClkInitTypeDef RCC_ClkInitStruct = {0};

  /** Supply configuration update enable
  */
  HAL_PWREx_ConfigSupply(PWR_LDO_SUPPLY);

  /** Configure the main internal regulator output voltage
  */
  __HAL_PWR_VOLTAGESCALING_CONFIG(PWR_REGULATOR_VOLTAGE_SCALE2);

  while(!__HAL_PWR_GET_FLAG(PWR_FLAG_VOSRDY)) {}

  /** Initializes the RCC Oscillators according to the specified parameters
  * in the RCC_OscInitTypeDef structure.
  */
  RCC_OscInitStruct.OscillatorType = RCC_OSCILLATORTYPE_HSI;
  RCC_OscInitStruct.HSIState = RCC_HSI_DIV1;
  RCC_OscInitStruct.HSICalibrationValue = 64;
  RCC_OscInitStruct.PLL.PLLState = RCC_PLL_ON;
  RCC_OscInitStruct.PLL.PLLSource = RCC_PLLSOURCE_HSI;
  RCC_OscInitStruct.PLL.PLLM = 4;
  RCC_OscInitStruct.PLL.PLLN = 12;
  RCC_OscInitStruct.PLL.PLLP = 1;
  RCC_OscInitStruct.PLL.PLLQ = 4;
  RCC_OscInitStruct.PLL.PLLR = 2;
  RCC_OscInitStruct.PLL.PLLRGE = RCC_PLL1VCIRANGE_3;
  RCC_OscInitStruct.PLL.PLLVCOSEL = RCC_PLL1VCOWIDE;
  RCC_OscInitStruct.PLL.PLLFRACN = 0;
  if (HAL_RCC_OscConfig(&RCC_OscInitStruct) != HAL_OK)
  {
    Error_Handler();
  }

  /** Initializes the CPU, AHB and APB buses clocks
  */
  RCC_ClkInitStruct.ClockType = RCC_CLOCKTYPE_HCLK|RCC_CLOCKTYPE_SYSCLK
                              |RCC_CLOCKTYPE_PCLK1|RCC_CLOCKTYPE_PCLK2
                              |RCC_CLOCKTYPE_D3PCLK1|RCC_CLOCKTYPE_D1PCLK1;
  RCC_ClkInitStruct.SYSCLKSource = RCC_SYSCLKSOURCE_PLLCLK;
  RCC_ClkInitStruct.SYSCLKDivider = RCC_SYSCLK_DIV1;
  RCC_ClkInitStruct.AHBCLKDivider = RCC_HCLK_DIV2;
  RCC_ClkInitStruct.APB3CLKDivider = RCC_APB3_DIV2;
  RCC_ClkInitStruct.APB1CLKDivider = RCC_APB1_DIV2;
  RCC_ClkInitStruct.APB2CLKDivider = RCC_APB2_DIV2;
  RCC_ClkInitStruct.APB4CLKDivider = RCC_APB4_DIV2;

  if (HAL_RCC_ClockConfig(&RCC_ClkInitStruct, FLASH_LATENCY_1) != HAL_OK)
  {
    Error_Handler();
  }
}

/**
  * @brief GPIO Initialization Function
  * @param None
  * @retval None
  */
static void MX_GPIO_Init(void)
{
  GPIO_InitTypeDef GPIO_InitStruct = {0};
  /* USER CODE BEGIN MX_GPIO_Init_1 */

  /* USER CODE END MX_GPIO_Init_1 */

  /* GPIO Ports Clock Enable */
  __HAL_RCC_GPIOC_CLK_ENABLE();
  __HAL_RCC_GPIOE_CLK_ENABLE();
  __HAL_RCC_GPIOA_CLK_ENABLE();
  __HAL_RCC_GPIOG_CLK_ENABLE();

  /*Configure GPIO pin Output Level */
  HAL_GPIO_WritePin(GPIOE, GPIO_PIN_9|GPIO_PIN_11|GPIO_PIN_14, GPIO_PIN_RESET);

  /*Configure GPIO pin Output Level */
  HAL_GPIO_WritePin(GPIOG, GPIO_PIN_12, GPIO_PIN_RESET);

  /*Configure GPIO pins : PE9 PE11 PE14 */
  GPIO_InitStruct.Pin = GPIO_PIN_9|GPIO_PIN_11|GPIO_PIN_14;
  GPIO_InitStruct.Mode = GPIO_MODE_OUTPUT_PP;
  GPIO_InitStruct.Pull = GPIO_NOPULL;
  GPIO_InitStruct.Speed = GPIO_SPEED_FREQ_LOW;
  HAL_GPIO_Init(GPIOE, &GPIO_InitStruct);

  /*Configure GPIO pin : PG12 */
  GPIO_InitStruct.Pin = GPIO_PIN_12;
  GPIO_InitStruct.Mode = GPIO_MODE_OUTPUT_PP;
  GPIO_InitStruct.Pull = GPIO_NOPULL;
  GPIO_InitStruct.Speed = GPIO_SPEED_FREQ_LOW;
  HAL_GPIO_Init(GPIOG, &GPIO_InitStruct);

  /* USER CODE BEGIN MX_GPIO_Init_2 */

  /* USER CODE END MX_GPIO_Init_2 */
}

/* USER CODE BEGIN 4 */
static void Console_StartRx(void)
{
  HAL_UART_Receive_IT(&hcom_uart[COM1], &dds_console_rx_byte, 1);
  dds_last_command_byte_tick = HAL_GetTick();
}

static void Console_ProcessCommand(void)
{
  char command[DDS_COMMAND_BUFFER_SIZE];

  memcpy(command, dds_command_buffer, dds_command_length);
  command[dds_command_length] = '\0';

  dds_command_length = 0U;
  dds_command_ready = 0U;
  dds_last_command_byte_tick = HAL_GetTick();

  if (command[0] == '\0')
  {
    return;
  }

  printf("[DDS] Acknowledged \"%s\"\r\n", command);

  if (strcmp(command, "status") == 0)
  {
    printf("[DDS] Requested %lu Hz, active %lu Hz\r\n",
           (unsigned long)dds_requested_frequency_hz,
           (unsigned long)dds_active_frequency_hz);
    printf("[VGA] Vctl=%.4f V, Gain=%.2f dB, slope=%.2f dB/V, offset=%.2f dB\r\n",
           (double)AD603_GetControlVoltage(&hvga),
           (double)AD603_GetGainDb(&hvga),
           (double)hvga.slope_db_per_v,
           (double)hvga.offset_db);
    return;
  }

  /* "mute" — drive AD603 to 0 V (minimum gain). */
  if (strcmp(command, "mute") == 0)
  {
    if (AD603_Mute(&hvga) == HAL_OK) {
      printf("[VGA] Muted (Vctl=0 V).\r\n");
    } else {
      printf("[VGA] Mute failed.\r\n");
    }
    return;
  }

  /* "gain <dB>" — request gain in dB. Driver clamps to safe range. */
  if (strncmp(command, "gain ", 5) == 0)
  {
    char *p = NULL;
    float db = (float)strtod(command + 5, &p);
    if ((p == command + 5) || (*p != '\0')) {
      printf("[VGA] Invalid: '%s'. Use: gain <dB>\r\n", command + 5);
      return;
    }
    if (AD603_SetGainDb(&hvga, db) != HAL_OK) {
      printf("[VGA] SetGainDb failed.\r\n");
      return;
    }
    printf("[VGA] Gain=%.2f dB (Vctl=%.4f V)\r\n",
           (double)AD603_GetGainDb(&hvga),
           (double)AD603_GetControlVoltage(&hvga));
    return;
  }

  /* "vctl <volts>" — request control voltage directly. Hard-clamped to 1.0 V. */
  if (strncmp(command, "vctl ", 5) == 0)
  {
    char *p = NULL;
    float v = (float)strtod(command + 5, &p);
    if ((p == command + 5) || (*p != '\0')) {
      printf("[VGA] Invalid: '%s'. Use: vctl <volts, 0..1>\r\n", command + 5);
      return;
    }
    if (AD603_SetControlVoltage(&hvga, v) != HAL_OK) {
      printf("[VGA] SetControlVoltage failed.\r\n");
      return;
    }
    printf("[VGA] Vctl=%.4f V (Gain=%.2f dB)\r\n",
           (double)AD603_GetControlVoltage(&hvga),
           (double)AD603_GetGainDb(&hvga));
    return;
  }

  /* "cal v1 db1 v2 db2" — two-point calibration (RAM only, lost on reset). */
  if (strncmp(command, "cal ", 4) == 0)
  {
    float v1, db1, v2, db2;
    char *p = command + 4;
    char *q;
    v1  = (float)strtod(p, &q); if (q == p) goto cal_err; p = q;
    db1 = (float)strtod(p, &q); if (q == p) goto cal_err; p = q;
    v2  = (float)strtod(p, &q); if (q == p) goto cal_err; p = q;
    db2 = (float)strtod(p, &q); if (q == p) goto cal_err;
    if (AD603_Calibrate(&hvga, v1, db1, v2, db2) != HAL_OK) {
      printf("[VGA] Calibration rejected (v1==v2, out of range, or bad slope).\r\n");
      return;
    }
    printf("[VGA] Calibrated. slope=%.3f dB/V, offset=%.3f dB\r\n",
           (double)hvga.slope_db_per_v,
           (double)hvga.offset_db);
    /* Re-mute after calibration so we never sit at a stale Vctl. */
    AD603_Mute(&hvga);
    return;
cal_err:
    printf("[VGA] Invalid: use 'cal <v1> <db1> <v2> <db2>'\r\n");
    return;
  }

  /* "sweep" / "sweep <start> <end> <step> <ms>" — gain ramp test. BLOCKING. */
  if (strncmp(command, "sweep", 5) == 0 &&
      (command[5] == '\0' || command[5] == ' '))
  {
    float    s = 0.0f, e = AD603_MAX_GAIN_DB, st = 5.0f;
    uint32_t ms = 200U;
    if (command[5] == ' ') {
      char *p = command + 6, *q;
      s  = (float)strtod(p, &q); if (q != p) p = q;
      e  = (float)strtod(p, &q); if (q != p) p = q;
      st = (float)strtod(p, &q); if (q != p) p = q;
      ms = (uint32_t)strtoul(p, &q, 10);
      if (ms == 0U) ms = 200U;
    }
    Sweep_Run(s, e, st, ms);
    return;
  }

  /* Parse numeric part (supports decimals, e.g. 7.7) */
  char *endptr = NULL;
  double value_d = strtod(command, &endptr);

  if (endptr == command)
  {
    printf("[DDS] Invalid command '%s'\r\n", command);
    return;
  }

  /* Skip optional whitespace between number and unit */
  while (*endptr == ' ') { endptr++; }

  /* Parse optional unit suffix (case-insensitive) */
  double multiplier = 1.0;
  char u0 = (char)((*endptr >= 'a') ? *endptr - 32 : *endptr);         /* uppercase first char  */
  char u1 = (char)((endptr[1] >= 'a') ? endptr[1] - 32 : endptr[1]);   /* uppercase second char */
  char u2 = (char)((endptr[2] >= 'a') ? endptr[2] - 32 : endptr[2]);   /* uppercase third char  */

  if (u0 == 'M' && u1 == 'H' && u2 == 'Z' && endptr[3] == '\0')
  {
    multiplier = 1000000.0; endptr += 3;
  }
  else if (u0 == 'M' && endptr[1] == '\0')
  {
    multiplier = 1000000.0; endptr += 1;
  }
  else if (u0 == 'K' && u1 == 'H' && u2 == 'Z' && endptr[3] == '\0')
  {
    multiplier = 1000.0; endptr += 3;
  }
  else if (u0 == 'K' && endptr[1] == '\0')
  {
    multiplier = 1000.0; endptr += 1;
  }
  else if (u0 == 'H' && u1 == 'Z' && endptr[2] == '\0')
  {
    /* explicit Hz — no scaling */ endptr += 2;
  }
  else if (*endptr != '\0')
  {
    printf("[DDS] Unknown unit in '%s'. Use Hz, kHz, or MHz.\r\n", command);
    return;
  }

  double scaled = value_d * multiplier + 0.5;
  if (scaled < 0.0)                   { scaled = 0.0; }
  if (scaled > (double)UINT32_MAX)    { scaled = (double)UINT32_MAX; }

  dds_requested_frequency_hz = (uint32_t)scaled;
  printf("[DDS] Requesting %lu Hz\r\n", (unsigned long)dds_requested_frequency_hz);
}

static void DDS_ApplyFrequency(void)
{
  uint32_t requested = dds_requested_frequency_hz;

  if (requested > DDS_MAX_FREQUENCY_HZ)
  {
    requested = DDS_MAX_FREQUENCY_HZ;
  }
  else if (requested < DDS_MIN_FREQUENCY_HZ)
  {
    requested = DDS_MIN_FREQUENCY_HZ;
  }

  AD9851_SetFrequency(&hdds, requested);
  dds_active_frequency_hz = requested;

  printf("[DDS] Applied %lu Hz\r\n", (unsigned long)dds_active_frequency_hz);
}

static void Sweep_Run(float db_start, float db_end, float db_step, uint32_t step_ms)
{
  /* Defensive bounds — driver clamps too, but keep loop sane. */
  if (db_step <= 0.0f) db_step = 1.0f;
  if (step_ms == 0U)   step_ms = 50U;
  if (db_start < AD603_MIN_GAIN_DB) db_start = AD603_MIN_GAIN_DB;
  if (db_end   > AD603_MAX_GAIN_DB) db_end   = AD603_MAX_GAIN_DB;

  printf("[VGA] Sweep %.1f -> %.1f dB step %.1f dB, %lu ms/step\r\n",
         (double)db_start, (double)db_end, (double)db_step,
         (unsigned long)step_ms);

  for (float g = db_start; g <= db_end + 0.001f; g += db_step)
  {
    AD603_SetGainDb(&hvga, g);
    printf("[VGA] %.2f dB  (Vctl=%.4f V)\r\n",
           (double)AD603_GetGainDb(&hvga),
           (double)AD603_GetControlVoltage(&hvga));
    HAL_Delay(step_ms);
  }

  /* SAFETY: always finish a sweep with the device muted. */
  AD603_Mute(&hvga);
  printf("[VGA] Sweep done. Muted.\r\n");
}

void HAL_UART_RxCpltCallback(UART_HandleTypeDef *huart)
{
  if (huart == &hcom_uart[COM1])
  {
    uint8_t byte = dds_console_rx_byte;

    if (dds_command_ready != 0U)
    {
      HAL_UART_Receive_IT(huart, &dds_console_rx_byte, 1);
      return;
    }

    dds_last_command_byte_tick = HAL_GetTick();

    if ((byte == '\r') || (byte == '\n'))
    {
      if (dds_command_length > 0U)
      {
        dds_command_ready = 1U;
      }
    }
    else
    {
      if (dds_command_length < (DDS_COMMAND_BUFFER_SIZE - 1U))
      {
        dds_command_buffer[dds_command_length++] = (char)byte;
      }
      else
      {
        dds_command_length = 0U;
        dds_command_overflow = 1U;
      }
    }

    HAL_UART_Receive_IT(huart, &dds_console_rx_byte, 1);
  }
}

/* USER CODE END 4 */

 /* MPU Configuration */

void MPU_Config(void)
{
  MPU_Region_InitTypeDef MPU_InitStruct = {0};

  /* Disables the MPU */
  HAL_MPU_Disable();

  /** Initializes and configures the Region and the memory to be protected
  */
  MPU_InitStruct.Enable = MPU_REGION_ENABLE;
  MPU_InitStruct.Number = MPU_REGION_NUMBER0;
  MPU_InitStruct.BaseAddress = 0x0;
  MPU_InitStruct.Size = MPU_REGION_SIZE_4GB;
  MPU_InitStruct.SubRegionDisable = 0x87;
  MPU_InitStruct.TypeExtField = MPU_TEX_LEVEL0;
  MPU_InitStruct.AccessPermission = MPU_REGION_NO_ACCESS;
  MPU_InitStruct.DisableExec = MPU_INSTRUCTION_ACCESS_DISABLE;
  MPU_InitStruct.IsShareable = MPU_ACCESS_SHAREABLE;
  MPU_InitStruct.IsCacheable = MPU_ACCESS_NOT_CACHEABLE;
  MPU_InitStruct.IsBufferable = MPU_ACCESS_NOT_BUFFERABLE;

  HAL_MPU_ConfigRegion(&MPU_InitStruct);
  /* Enables the MPU */
  HAL_MPU_Enable(MPU_PRIVILEGED_DEFAULT);

}

/**
  * @brief  This function is executed in case of error occurrence.
  * @retval None
  */
void Error_Handler(void)
{
  /* USER CODE BEGIN Error_Handler_Debug */
  /* User can add his own implementation to report the HAL error return state */
  __disable_irq();
  while (1)
  {
  }
  /* USER CODE END Error_Handler_Debug */
}
#ifdef USE_FULL_ASSERT
/**
  * @brief  Reports the name of the source file and the source line number
  *         where the assert_param error has occurred.
  * @param  file: pointer to the source file name
  * @param  line: assert_param error line source number
  * @retval None
  */
void assert_failed(uint8_t *file, uint32_t line)
{
  /* USER CODE BEGIN 6 */
  /* User can add his own implementation to report the file name and line number,
     ex: printf("Wrong parameters value: file %s on line %d\r\n", file, line) */
  /* USER CODE END 6 */
}
#endif /* USE_FULL_ASSERT */
