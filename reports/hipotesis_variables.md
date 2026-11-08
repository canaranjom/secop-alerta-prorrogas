# Hipótesis de variables

**Proyecto:** Alerta temprana de prórrogas en contratos públicos (SECOP II)
**Entrega:** 1 (formulación) · actualizado en la Entrega 2 con el resultado en el modelo · Despliegue de Soluciones Analíticas · MIAD, Universidad de los Andes
**Responsable:** Julián David Castañeda Plazas

## Propósito

Este documento formula, para cada variable candidata, la hipótesis de negocio que explicaría su relación con la prórroga del contrato, la evidencia que aporta la exploración de datos y si la variable se conoce al momento de la firma. Esta última condición determina si la variable puede entrar al modelo: solo se admite información disponible antes de firmar.

Las cifras de la exploración provienen del reporte de la Entrega 1 y del notebook `notebooks/01_exploracion_secop.ipynb` (contratos SECOP II firmados en 2023–2024 y terminados al corte del 1-oct-2026; tasa nacional de prórroga: 12,2 %). La columna **Resultado en el modelo** se agregó en la Entrega 2 con el análisis SHAP del modelo elegido (sección 4).

## 1. Variables candidatas

| Variable | Hipótesis (por qué influiría en que el contrato se prorrogue) | Evidencia de la exploración | ¿Se conoce al firmar? | Resultado en el modelo (Entrega 2) |
|---|---|---|---|---|
| Tipo de contrato | Los objetos con ejecución técnica o física (obra, interventoría, consultoría) dependen de factores externos e imprevistos; la interventoría, además, se extiende cuando se extiende la obra que vigila. | Interventoría 46,2 %, obra 23,7 % y consultoría 21,8 %, frente a 12,2 % nacional; suministros 7,3 % y compraventa 9,2 % (Figura 2). | Sí | **Matizada.** No está entre las 15 variables más importantes (< 1,4 %): su información la recogen la duración pactada, la justificación de la modalidad (3,9 %) y el tipo × tramo de precio (3,1 %). |
| Modalidad de contratación | Las modalidades competitivas se emplean para objetos de mayor tamaño y complejidad, por lo que la modalidad actúa como indicador de la complejidad del contrato. | Licitación de obra pública 44 % y concurso de méritos 41 %, frente a contratación directa 11 % y mínima cuantía 8 %. | Sí | **Matizada.** Igual que el tipo de contrato: la modalidad no aparece entre las 15 más importantes; la justificación de la modalidad sí (3,9 %). |
| Duración pactada | A mayor plazo, mayor exposición a imprevistos; además, los plazos tienden a subestimarse al planear (falacia de planeación; Buehler, Griffin y Ross, 1994). | De 7,0 % (≤ 1 mes) a 49,8 % (1–2 años), siete veces más; > 2 años: 36,5 % (Figura 3). La relación no es lineal: 6–9 meses 19,2 % y 9–12 meses 15,4 %. | Sí. Se convierte a días desde el texto pactado y se recorta en el percentil 99 (390 días). | **Confirmada.** Es la variable más importante (21,8 %): a más días pactados, más riesgo. |
| Precio base del proceso | El monto es un indicador del tamaño y la complejidad del contrato; en proyectos de gran escala los incumplimientos de plazo son frecuentes (Flyvbjerg, 2014). | La tasa sube de 9 % en el decil más bajo a 20 % en el más alto. Interacción con el tipo: en obra pasa de 4 % (< 10 millones) a 43 % (> 1.000 millones) y en interventoría de 32 % a 64 %. | Sí. Se usa el precio base del proceso, no el valor del contrato (ver sección 2). | **Matizada.** Pesa 3,8 % y, a igual duración y entidad, un precio alto baja levemente el riesgo: el efecto del monto pasa por la duración. |
| Entidad contratante | Cada entidad tiene capacidades de planeación y prácticas de supervisión propias, que se reflejan en la frecuencia con que prorroga sus contratos. | Entre 1.612 entidades con al menos 100 contratos, la tasa va de 0 % (percentil 10) a 22 % (percentil 90). Es persistente: correlación de 0,53 entre la tasa de 2023 y la de 2024. | Sí, expresada como tasa histórica de la entidad y no como identificador (ver sección 3). | **Confirmada.** La tasa histórica de la entidad es la tercera variable (12,4 %), más el volumen de contratos previos de la entidad (7,1 %). |
| Sector | Cada sector tiene dinámicas propias de demanda y de ejecución que condicionan el cumplimiento de los plazos. | Salud y Protección Social presenta la tasa más alta: 18 %. | Sí | **Confirmada** (7,3 %). Servicio Público y Salud y Protección Social suben el riesgo; Tecnologías de la Información, Hacienda y Planeación lo bajan. |
| Competencia del proceso | Los procesos con más oferentes corresponden a contratos de mayor tamaño y atractivo; el efecto probablemente está confundido con el monto. | Procesos con más de cinco ofertas: 18 %; con una o dos ofertas: 11 %. | Sí, se conoce al adjudicar. | **Débil, como se anticipó.** Las variables de competencia no aparecen entre las 15 más importantes (< 1,4 % cada una), coherente con un efecto absorbido por el tamaño y la duración. |
| Proveedor (antigüedad, condición de pyme) | La experiencia y la capacidad del contratista influirían en el cumplimiento de los plazos. | La antigüedad y la condición de pyme cambian la tasa en menos de 4 puntos; el tamaño de empresa es "No Definido" en 90 % de los registros. | Sí, pero aporta poco por sí solo. | **Confirmada (aporta poco).** Tasa histórica del proveedor 1,8 % y antigüedad 1,4 %. |

## 2. Variables excluidas por fuga de información

| Variable | ¿Se conoce al firmar? | Motivo |
|---|---|---|
| `valor_del_contrato` y derivados | No, es fuga. | Se actualiza con las adiciones: cuando el valor final es igual al precio base solo 2 % de los contratos se prorroga; cuando lo supera, entre 36 % y 53 %. |
| `valor_pagado`, `valor_facturado`, `valor_pendiente_de_ejecucion` | No, es fuga. | Corresponden a la ejecución, posterior a la firma. |
| `estado_contrato`, `liquidacion`, `ultima_actualizacion` | No, es fuga. | Describen el estado posterior a la firma. |
| `fecha_de_fin_del_contrato`, duración real | No, es fuga. | Pueden incluir la prórroga. |

## 3. Variables nuevas que vale la pena construir

1. **Tasa histórica de prórroga de la entidad.** La persistencia entre años (correlación de 0,53) indica que el comportamiento pasado de la entidad anticipa el futuro. Resume en una sola variable numérica la información de 1.612 entidades, que como identificador categórico sería difícil de usar. Debe calcularse solo con contratos terminados antes de cada firma; de lo contrario, se introduciría fuga temporal.
   - *Resultado en el modelo (Entrega 2):* **confirmada.** Fue la variable nueva que más aportó: tercera en importancia (12,4 %), más el volumen de contratos previos de la entidad (7,1 %).

2. **Interacción entre tipo de contrato y tramo de precio base.** El efecto del monto depende del tipo: en obra la tasa pasa de 4 % a 43 % según el precio base, mientras que en el conjunto de contratos solo va de 9 % a 20 %. Los modelos de árboles pueden capturar esta interacción por sí mismos, pero hacerla explícita mejora la línea base de regresión logística y facilita la interpretación en el tablero.
   - *Resultado en el modelo (Entrega 2):* **confirmada.** Los modelos de árboles, que capturan interacciones, superan a la regresión logística (AUC 0,815 de LightGBM frente a 0,737), y la variable aporta 3,1 % de la importancia del modelo elegido.

3. **Indicador de plazo que supera la vigencia fiscal (duración pactada mayor a 12 meses).** La tasa salta de 15,4 % (9–12 meses) a 49,8 % (1–2 años). Se plantea como hipótesis por validar en la Entrega 2: en Colombia el año fiscal va del 1 de enero al 31 de diciembre (principio de anualidad, artículo 14 del Estatuto Orgánico del Presupuesto, Decreto 111 de 1996), y los contratos que se extienden más allá de una vigencia requieren mecanismos presupuestales excepcionales, como vigencias futuras o reservas (Colombia Compra Eficiente, 2025), lo que podría asociarse con ajustes de plazo.
   - *Resultado en el modelo (Entrega 2):* **no se confirma como se planteó.** Una vez considerada la duración pactada, el indicador de plazo que cruza la vigencia fiscal tiene un efecto pequeño y negativo, y el de duración mayor a 12 meses no aparece entre las 15 variables más importantes: su información ya la contiene la duración. En cambio, el mes de firma pesa 6,6 % y firmar a final de año sube el riesgo, lo que mantiene abierta una relación con el calendario presupuestal.

## 4. Contraste con el modelo (Entrega 2)

**Método.** Se usaron los valores SHAP del modelo elegido (LightGBM `lgbm-base`, registrado en MLflow como `secop-prorroga` v1), calculados de forma exacta para árboles (Lundberg y Lee, 2017; Lundberg et al., 2020) sobre una muestra de 20.000 contratos de validación (`notebooks/02_modelo_y_shap.ipynb`). La importancia de cada variable es su promedio de |SHAP| expresado como porcentaje de la suma de todas; el signo del SHAP indica si la variable sube o baja el riesgo. Una hipótesis se considera **confirmada** si la variable tiene importancia relevante y el efecto va en la dirección esperada; **matizada** si su información la recogen otras variables; y **no confirmada** si su efecto es mínimo o contrario una vez consideradas las demás.

**Hallazgo nuevo (no planteado en la Entrega 1).** El departamento es la segunda variable más importante (12,9 %): Putumayo, La Guajira, Bogotá y Cundinamarca suben el riesgo; Casanare, San Andrés y Huila lo bajan.

**Advertencia.** SHAP describe qué usa el modelo para predecir, no qué causa la prórroga; cada efecto se lee manteniendo constantes las demás variables.

## Referencias

- Buehler, R., Griffin, D. y Ross, M. (1994). Exploring the "planning fallacy": Why people underestimate their task completion times. *Journal of Personality and Social Psychology, 67*(3), 366–381.
- Colombia Compra Eficiente. (2025). *Concepto C-300 de 2025*. Relatoría. https://relatoria.colombiacompra.gov.co/conceptos/c-300-de-2025/
- Flyvbjerg, B. (2014). What you should know about megaprojects and why: An overview. *Project Management Journal, 45*(2), 6–19. https://doi.org/10.1002/pmj.21408
- Presidencia de la República de Colombia. (1996). *Decreto 111 de 1996, por el cual se compilan las normas que conforman el Estatuto Orgánico del Presupuesto*.
- Lundberg, S. M. y Lee, S.-I. (2017). A unified approach to interpreting model predictions. *Advances in Neural Information Processing Systems, 30*, 4765–4774.
- Lundberg, S. M., Erion, G., Chen, H., DeGrave, A., Prutkin, J. M., Nair, B., Katz, R., Himmelfarb, J., Bansal, N. y Lee, S.-I. (2020). From local explanations to global understanding with explainable AI for trees. *Nature Machine Intelligence, 2*(1), 56–67.
