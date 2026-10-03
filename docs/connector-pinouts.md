# Revision A.3 connector pin reference

Native pin numbers; use the square/pin-1 mark. Every interface is2.54mm. Only FIELD pins have the±100V design tolerance. J5.9 is a high-impedance OE monitor, not an enable-control input.

## J1 — 2P / 2.54mm

5.0-5.25Vregulated,>=1A.

| Pin | Net |
|---:|---|
| 1 | `+5V_LOGIC` |
| 2 | `GND` |

## J2 — 2P / 2.54mm

12 V raw,>=0.5A;externalvalvefeedsseparate.

| Pin | Net |
|---:|---|
| 1 | `+12V_IN` |
| 2 | `GND` |

## J3 — 20P / 2.54mm



| Pin | Net |
|---:|---|
| 1 | `GND` |
| 2 | `+3V3` |
| 3 | `ESP_EN` |
| 4 | `MCU_MOSI_GPIO4` |
| 5 | `SPI_MISO_GPIO5` |
| 6 | `MCU_CLK_GPIO6` |
| 7 | `MCU_LATCH_GPIO7` |
| 8 | `MCU_INHIBIT_N_GPIO15` |
| 9 | `MCU_CLR_N_GPIO16` |
| 10 | `ESTOP_SAFE_MON_GPIO18` |
| 11 | `MCU_LOAD_N_GPIO17` |
| 12 | `I2C_SDA_GPIO8` |
| 13 | `USB_DM_GPIO19` |
| 14 | `USB_DP_GPIO20` |
| 15 | `GPIO3` |
| 16 | `GPIO46` |
| 17 | `I2C_SCL_GPIO9` |
| 18 | `GPIO10` |
| 19 | `GPIO11` |
| 20 | `GPIO12` |

## J4 — 20P / 2.54mm



| Pin | Net |
|---:|---|
| 1 | `GPIO13` |
| 2 | `GPIO14` |
| 3 | `HW_RUN_MON_GPIO21` |
| 4 | `GPIO47` |
| 5 | `GPIO48` |
| 6 | `GPIO45` |
| 7 | `BOOT_GPIO0` |
| 8 | `GPIO35` |
| 9 | `GPIO36` |
| 10 | `GPIO37` |
| 11 | `GPIO38` |
| 12 | `GPIO39` |
| 13 | `GPIO40` |
| 14 | `GPIO41` |
| 15 | `GPIO42` |
| 16 | `UART_RX_GPIO44` |
| 17 | `UART_TX_GPIO43` |
| 18 | `ROLE_GPIO2_MON` |
| 19 | `GPIO1` |
| 20 | `GND` |

## J5 — 20P / 2.54mm

Debug only; pins3/4 are5V/12V. Hardware status monitors isolated. Never injectcoil power.

| Pin | Net |
|---:|---|
| 1 | `GND` |
| 2 | `+3V3` |
| 3 | `+5V_LOGIC` |
| 4 | `+12V_IN` |
| 5 | `BUS_CLK` |
| 6 | `BUS_LOAD_N` |
| 7 | `BUS_LATCH` |
| 8 | `BUS_CLR_N` |
| 9 | `OE_MONITOR_N` |
| 10 | `HW_RUN_MON_GPIO21` |
| 11 | `ESTOP_SAFE_MON_GPIO18` |
| 12 | `ROLE_GPIO2_MON` |
| 13 | `RLY1_CMD` |
| 14 | `RLY2_CMD` |
| 15 | `RLY3_CMD` |
| 16 | `RLY4_CMD` |
| 17 | `RLY5_CMD` |
| 18 | `RLY6_CMD` |
| 19 | `RLY7_CMD` |
| 20 | `RLY8_CMD` |

## J6 — 3P / 2.54mm

Reset1-2;BOOT3-2 heldduringresetforROMdownload.

| Pin | Net |
|---:|---|
| 1 | `ESP_EN` |
| 2 | `GND` |
| 3 | `BOOT_GPIO0` |

## J7 — 3P / 2.54mm

3.3VUART,self-poweredboard.

| Pin | Net |
|---:|---|
| 1 | `UART_TX_GPIO43` |
| 2 | `UART_RX_GPIO44` |
| 3 | `GND` |

## J9 — 2P / 2.54mm

ExternalNCcontactbetween1/2,serieschain.

| Pin | Net |
|---:|---|
| 1 | `ESTOP_FIELD` |
| 2 | `ESTOP_CHAIN_OUT` |

## J10 — 2P / 2.54mm

LASTMODULEterminationonly;removeintermediatejumpers.

| Pin | Net |
|---:|---|
| 1 | `ESTOP_CHAIN_OUT` |
| 2 | `GND` |

## J11 — 2P / 2.54mm

DrycontacttoGND;20mAboard-sourced;fieldfaultlimit+/-100V.

| Pin | Net |
|---:|---|
| 1 | `IN1_FIELD` |
| 2 | `GND` |

## J12 — 2P / 2.54mm

DrycontacttoGND;20mAboard-sourced;fieldfaultlimit+/-100V.

| Pin | Net |
|---:|---|
| 1 | `IN2_FIELD` |
| 2 | `GND` |

## J13 — 2P / 2.54mm

DrycontacttoGND;20mAboard-sourced;fieldfaultlimit+/-100V.

| Pin | Net |
|---:|---|
| 1 | `IN3_FIELD` |
| 2 | `GND` |

## J14 — 2P / 2.54mm

DrycontacttoGND;20mAboard-sourced;fieldfaultlimit+/-100V.

| Pin | Net |
|---:|---|
| 1 | `IN4_FIELD` |
| 2 | `GND` |

## J15 — 2P / 2.54mm

DrycontacttoGND;20mAboard-sourced;fieldfaultlimit+/-100V.

| Pin | Net |
|---:|---|
| 1 | `IN5_FIELD` |
| 2 | `GND` |

## J16 — 2P / 2.54mm

DrycontacttoGND;20mAboard-sourced;fieldfaultlimit+/-100V.

| Pin | Net |
|---:|---|
| 1 | `IN6_FIELD` |
| 2 | `GND` |

## J17 — 2P / 2.54mm

DrycontacttoGND;20mAboard-sourced;fieldfaultlimit+/-100V.

| Pin | Net |
|---:|---|
| 1 | `IN7_FIELD` |
| 2 | `GND` |

## J18 — 2P / 2.54mm

DrycontacttoGND;20mAboard-sourced;fieldfaultlimit+/-100V.

| Pin | Net |
|---:|---|
| 1 | `IN8_FIELD` |
| 2 | `GND` |

## J20 — EXP_UP

NOPOWERPINS;independentlocalsupplies. Pin11NCcontinuity,terminateonlylast.

| Pin | Net |
|---:|---|
| 1 | `GND` |
| 2 | `GND` |
| 3 | `UP_CLK` |
| 4 | `UP_SER` |
| 5 | `UP_RETURN` |
| 6 | `UP_LATCH` |
| 7 | `UP_ARM_N` |
| 8 | `UP_CLR_N` |
| 9 | `UP_LOAD_N` |
| 10 | `GND` |
| 11 | `ESTOP_FIELD` |
| 12 | `GND` |
| 13 | `GND` |
| 14 | `GND` |
| 15 | `I2C_SDA_BUS` |
| 16 | `I2C_SCL_BUS` |

## J21 — EXP_DOWN

NOPOWERPINS;independentlocalsupplies. Pin11NCcontinuity,terminateonlylast.

| Pin | Net |
|---:|---|
| 1 | `GND` |
| 2 | `GND` |
| 3 | `DOWN_CLK` |
| 4 | `DOWN_SER` |
| 5 | `DOWN_RETURN` |
| 6 | `DOWN_LATCH` |
| 7 | `DOWN_ARM_N` |
| 8 | `DOWN_CLR_N` |
| 9 | `DOWN_LOAD_N` |
| 10 | `GND` |
| 11 | `ESTOP_CHAIN_OUT` |
| 12 | `GND` |
| 13 | `GND` |
| 14 | `GND` |
| 15 | `I2C_SDA_BUS` |
| 16 | `I2C_SCL_BUS` |

## J31 — 3P / 2.54mm

1COM fused12V, 2NO valve, 3NC auxiliary.

| Pin | Net |
|---:|---|
| 1 | `VALVE1_COM` |
| 2 | `VALVE1_NO` |
| 3 | `VALVE1_NC_AUX` |

## J32 — 3P / 2.54mm

1COM fused12V, 2NO valve, 3NC auxiliary.

| Pin | Net |
|---:|---|
| 1 | `VALVE2_COM` |
| 2 | `VALVE2_NO` |
| 3 | `VALVE2_NC_AUX` |

## J33 — 3P / 2.54mm

1COM fused12V, 2NO valve, 3NC auxiliary.

| Pin | Net |
|---:|---|
| 1 | `VALVE3_COM` |
| 2 | `VALVE3_NO` |
| 3 | `VALVE3_NC_AUX` |

## J34 — 3P / 2.54mm

1COM fused12V, 2NO valve, 3NC auxiliary.

| Pin | Net |
|---:|---|
| 1 | `VALVE4_COM` |
| 2 | `VALVE4_NO` |
| 3 | `VALVE4_NC_AUX` |

## J35 — 3P / 2.54mm

1COM fused12V, 2NO valve, 3NC auxiliary.

| Pin | Net |
|---:|---|
| 1 | `VALVE5_COM` |
| 2 | `VALVE5_NO` |
| 3 | `VALVE5_NC_AUX` |

## J36 — 3P / 2.54mm

1COM fused12V, 2NO valve, 3NC auxiliary.

| Pin | Net |
|---:|---|
| 1 | `VALVE6_COM` |
| 2 | `VALVE6_NO` |
| 3 | `VALVE6_NC_AUX` |

## J37 — 3P / 2.54mm

1COM fused12V, 2NO valve, 3NC auxiliary.

| Pin | Net |
|---:|---|
| 1 | `VALVE7_COM` |
| 2 | `VALVE7_NO` |
| 3 | `VALVE7_NC_AUX` |

## J38 — 3P / 2.54mm

1COM fused12V, 2NO valve, 3NC auxiliary.

| Pin | Net |
|---:|---|
| 1 | `VALVE8_COM` |
| 2 | `VALVE8_NO` |
| 3 | `VALVE8_NC_AUX` |

## J41 — 2P / 2.54mm

Valve positiveNO, negativeRETURN. Independent external fusedpower.

| Pin | Net |
|---:|---|
| 1 | `VALVE1_NO` |
| 2 | `VALVE1_RETURN` |

## J42 — 2P / 2.54mm

Valve positiveNO, negativeRETURN. Independent external fusedpower.

| Pin | Net |
|---:|---|
| 1 | `VALVE2_NO` |
| 2 | `VALVE2_RETURN` |

## J43 — 2P / 2.54mm

Valve positiveNO, negativeRETURN. Independent external fusedpower.

| Pin | Net |
|---:|---|
| 1 | `VALVE3_NO` |
| 2 | `VALVE3_RETURN` |

## J44 — 2P / 2.54mm

Valve positiveNO, negativeRETURN. Independent external fusedpower.

| Pin | Net |
|---:|---|
| 1 | `VALVE4_NO` |
| 2 | `VALVE4_RETURN` |

## J45 — 2P / 2.54mm

Valve positiveNO, negativeRETURN. Independent external fusedpower.

| Pin | Net |
|---:|---|
| 1 | `VALVE5_NO` |
| 2 | `VALVE5_RETURN` |

## J46 — 2P / 2.54mm

Valve positiveNO, negativeRETURN. Independent external fusedpower.

| Pin | Net |
|---:|---|
| 1 | `VALVE6_NO` |
| 2 | `VALVE6_RETURN` |

## J47 — 2P / 2.54mm

Valve positiveNO, negativeRETURN. Independent external fusedpower.

| Pin | Net |
|---:|---|
| 1 | `VALVE7_NO` |
| 2 | `VALVE7_RETURN` |

## J48 — 2P / 2.54mm

Valve positiveNO, negativeRETURN. Independent external fusedpower.

| Pin | Net |
|---:|---|
| 1 | `VALVE8_NO` |
| 2 | `VALVE8_RETURN` |

## JP1 — 2P / 2.54mm

Closed=master;open=expander. Exactlyonehost.

| Pin | Net |
|---:|---|
| 1 | `LOCAL_MASTER_N` |
| 2 | `GND` |

## JP2 — 2P / 2.54mm

Close only one common-A pullup pair, normally master. No shared power pins.

| Pin | Net |
|---:|---|
| 1 | `+3V3` |
| 2 | `I2C_PULLUP_RAIL` |
