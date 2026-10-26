# Revisión de la pregunta de negocio y del alcance

**Proyecto:** Alerta temprana de prórrogas en contratos públicos (SECOP II)
**Entrega:** 1 · Despliegue de Soluciones Analíticas · MIAD, Universidad de los Andes
**Responsable:** Julián David Castañeda Plazas

## Propósito y criterio de revisión

Este documento revisa la pregunta de negocio y el alcance definidos en la sección 2 del reporte de la Entrega 1. Se toma como referencia la fase de entendimiento del negocio de CRISP-DM, que exige precisar el objetivo de negocio, el criterio de éxito de negocio, su traducción a un objetivo analítico y los riesgos y restricciones del proyecto (Chapman et al., 2000). Las cifras citadas provienen del reporte de la Entrega 1.

**Pregunta revisada:** con la información disponible al firmar un contrato en SECOP II, ¿qué tan probable es que requiera una prórroga, y qué contratos deberían priorizarse para seguimiento?

## 1. Fortalezas

1. **El momento de la predicción.** La expresión "al firmar" delimita qué información puede usar el modelo y es coherente con el control de fuga de información de la sección 4.6 del reporte, que excluye `valor_del_contrato` y las variables de ejecución.
2. **La pregunta se corresponde con el producto.** La primera parte de la pregunta: "¿qué tan probable…?", responde el modelo en la pantalla 1 que corresponde a la evaluación de los contratos dentro de la maqueta; la segunda: "¿qué contratos priorizar?", la responde la lista de contratos de mayor riesgo en la pantalla 2 que corresponde a la de los panoramas descriptivos.
3. **La variable objetivo y la población están definidas de forma operativa.** `prorrogado = 1` si `dias_adicionados > 0`, sobre contratos firmados entre enero de 2023 y diciembre de 2024 y terminados antes del 1 de octubre de 2026.
4. **El alcance delimita lo que el producto no hace.** Excluye predecir la duración de la prórroga, calificar entidades o contratistas y emitir conclusiones sobre irregularidades, lo que reduce el riesgo de un uso indebido de la señal.

## 2. Observaciones y recomendaciones

| # | Observación | Riesgo | Recomendación para la Entrega 2 |
|---|---|---|---|
| 1 | No se explicita un **criterio de éxito de negocio**. El usuario (un órgano de control) solo puede revisar un número limitado de contratos, y las métricas propuestas (AUC-PR y recall en la clase prorrogada) no reflejan esa restricción de capacidad. | Seleccionar un modelo con buen desempeño global que no mejore la priorización en la parte alta del ranking, que es la que usa el analista. | Definir la meta en función de la capacidad de revisión: recall y precisión en el k % de contratos con mayor riesgo (curva de lift), y fijar k con el usuario objetivo (Provost y Fawcett, 2013). |
| 2 | **Posible sesgo por censura en 2024.** La población solo incluye contratos terminados antes del corte. Un contrato largo firmado a fines de 2024 que fue prorrogado tiene mayor probabilidad de seguir abierto al corte y, por lo tanto, de quedar excluido. El riesgo es mayor en los contratos de 1 a 2 años, cuya tasa de prórroga es de 49,8 %. | Subestimar la tasa de prórroga justamente en el conjunto de prueba (2024) y sesgar la evaluación de la validación temporal. | Antes de fijar la validación, revisar la tasa por mes de firma en el segundo semestre de 2024 y la proporción de contratos excluidos por seguir abiertos; si hay sesgo, acortar la ventana de prueba o documentar la limitación (Klein y Moeschberger, 2003). |
| 3 | Los niveles de riesgo de la maqueta (bajo < 25 %, medio 25–50 %, alto > 50 %) interpretan la salida del modelo como una **probabilidad**. | Los modelos de árboles y de *boosting* suelen producir probabilidades mal calibradas, de modo que los niveles mostrados al usuario no corresponderían a frecuencias reales (Niculescu-Mizil y Caruana, 2005). | Incluir en el alcance un paso de calibración (por ejemplo, Platt o regresión isotónica) y evaluarlo con una curva de confiabilidad antes de fijar los umbrales. |
| 4 | La pantalla 2 incluye la **lista de contratos en ejecución con mayor probabilidad de prórroga**. Esto exige calificar periódicamente los contratos vigentes (inferencia por lotes), y no solo atender solicitudes individuales a través de la API. | Ampliar el alcance técnico y el consumo de recursos en la nube más allá del prototipo previsto, con un presupuesto limitado en AWS Academy. | Decidir en la Entrega 2 si la lista se precalcula sobre un corte fijo o una muestra de contratos vigentes, y dejar explícito en el alcance que su actualización no es en tiempo real. |

## 3. Conclusión

La pregunta de negocio es pertinente, está alineada con el producto y es coherente con el control de fuga de información. Se recomienda complementarla con un criterio de éxito de negocio basado en la capacidad de revisión del usuario y precisar en el alcance tres decisiones para la Entrega 2: el tratamiento de la posible censura en el conjunto de prueba, la calibración de las probabilidades y la forma de generar la lista de contratos en ejecución.

## Referencias

- Chapman, P., Clinton, J., Kerber, R., Khabaza, T., Reinartz, T., Shearer, C. y Wirth, R. (2000). *CRISP-DM 1.0: Step-by-step data mining guide*. SPSS.
- Klein, J. P. y Moeschberger, M. L. (2003). *Survival analysis: Techniques for censored and truncated data* (2.ª ed.). Springer.
- Niculescu-Mizil, A. y Caruana, R. (2005). Predicting good probabilities with supervised learning. En *Proceedings of the 22nd International Conference on Machine Learning (ICML)* (pp. 625–632).
- Provost, F. y Fawcett, T. (2013). *Data science for business: What you need to know about data mining and data-analytic thinking*. O'Reilly Media.
