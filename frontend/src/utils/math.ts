import { BudgetMatrix } from '../types/budget';

/**
 * Convierte un string o número monetario a centavos enteros para evitar imprecisiones de coma flotante.
 */
export function parseToCents(value: string | number | undefined | null): number {
  if (value === undefined || value === null || value === '') return 0;
  const str = String(value).trim().replace(',', '.');
  const cleaned = str.replace(/[^0-9.-]/g, '');
  if (!cleaned || isNaN(Number(cleaned))) return 0;
  
  // Dividir en parte entera y decimal
  const parts = cleaned.split('.');
  const intPart = parseInt(parts[0] || '0', 10);
  let decPart = parts[1] || '';
  if (decPart.length === 1) decPart += '0';
  else if (decPart.length > 2) decPart = decPart.substring(0, 2);
  else if (decPart.length === 0) decPart = '00';
  
  const sign = cleaned.startsWith('-') ? -1 : 1;
  const absInt = Math.abs(intPart);
  const cents = absInt * 100 + parseInt(decPart, 10);
  return sign * cents;
}

/**
 * Convierte centavos a formato string decimal fijo de dos decimales (ej. 1250 -> "12.50").
 */
export function centsToString(cents: number): string {
  const isNegative = cents < 0;
  const abs = Math.abs(cents);
  const intVal = Math.floor(abs / 100);
  const decVal = abs % 100;
  const decStr = decVal < 10 ? `0${decVal}` : `${decVal}`;
  return `${isNegative ? '-' : ''}${intVal}.${decStr}`;
}

export function formatCurrencyDisplay(val: string | number): string {
  const cents = parseToCents(val);
  const isNegative = cents < 0;
  const abs = Math.abs(cents);
  const intVal = Math.floor(abs / 100);
  const decVal = abs % 100;
  const formattedInt = intVal.toLocaleString('es-EC');
  const decStr = decVal < 10 ? `0${decVal}` : `${decVal}`;
  return `${isNegative ? '-$' : '$'}${formattedInt}.${decStr}`;
}

/**
 * Motor de cálculo reactivo que ejecuta las 6 reglas de cálculo especificadas:
 * 1. Total mensual de cada cuenta
 * 2. Total anual de cada cuenta
 * 3. Total mensual de cada categoría
 * 4. Total anual de cada categoría
 * 5. Total mensual general
 * 6. Total anual general y cuadre cruzado
 */
export function recalculateMatrixLocally(matrix: BudgetMatrix): BudgetMatrix {
  const newMatrix: BudgetMatrix = JSON.parse(JSON.stringify(matrix));

  const generalMonthlyCents: { [m: number]: number } = {};
  for (let m = 1; m <= 12; m++) generalMonthlyCents[m] = 0;
  let generalAnnualCents = 0;

  newMatrix.categories.forEach(cat => {
    const catMonthlyCents: { [m: number]: number } = {};
    for (let m = 1; m <= 12; m++) catMonthlyCents[m] = 0;
    let catAnnualCents = 0;

    cat.accounts.forEach(acc => {
      let accAnnualCents = 0;
      for (let m = 1; m <= 12; m++) {
        const monthCents = Math.max(0, parseToCents(acc.months[m] || '0.00')); // Restricción >= 0
        // Preservar texto mientras escribe; no sobrescribir acc.months[m]
        accAnnualCents += monthCents;
        catMonthlyCents[m] += monthCents;
      }
      acc.annual_total = centsToString(accAnnualCents);
      catAnnualCents += accAnnualCents;
    });

    cat.annual_total = centsToString(catAnnualCents);
    for (let m = 1; m <= 12; m++) {
      cat.monthly_totals[m] = centsToString(catMonthlyCents[m]);
      generalMonthlyCents[m] += catMonthlyCents[m];
    }
    generalAnnualCents += catAnnualCents;
  });

  for (let m = 1; m <= 12; m++) {
    newMatrix.general_monthly_totals[m] = centsToString(generalMonthlyCents[m]);
  }
  newMatrix.general_annual_total = centsToString(generalAnnualCents);

  // Verificación de cuadre horizontal vs vertical
  let sumMonthlyGeneralCents = 0;
  for (let m = 1; m <= 12; m++) sumMonthlyGeneralCents += generalMonthlyCents[m];
  newMatrix.is_balanced = (sumMonthlyGeneralCents === generalAnnualCents);

  return newMatrix;
}
