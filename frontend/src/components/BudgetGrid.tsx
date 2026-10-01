import React, { useState } from 'react';
import { BudgetMatrix } from '../types/budget';
import { formatCurrencyDisplay, parseToCents } from '../utils/math';

interface BudgetGridProps {
  matrix: BudgetMatrix;
  onCellChange: (accountId: number, month: number, newAmount: string) => void;
  onReplicateJanuary?: (accountId: number, amount: string) => void;
  pendingChangesCount: number;
  onSave: (modifiedBy: string, reason: string) => void;
  onDiscard: () => void;
  isSaving: boolean;
  userDefault: string;
}

const MONTH_NAMES = [
  'Enero', 'Febrero', 'Marzo', 'Abril', 'Mayo', 'Junio',
  'Julio', 'Agosto', 'Septiembre', 'Octubre', 'Noviembre', 'Diciembre'
];

export const BudgetGrid: React.FC<BudgetGridProps> = ({
  matrix,
  onCellChange,
  onReplicateJanuary,
  pendingChangesCount,
  onSave,
  onDiscard,
  isSaving,
  userDefault
}) => {
  const [collapsedCategories, setCollapsedCategories] = useState<{ [id: number]: boolean }>({});
  const [modifiedBy, setModifiedBy] = useState(userDefault || 'amoreno');
  const [reason, setReason] = useState('');

  const toggleCategory = (catId: number) => {
    setCollapsedCategories(prev => ({
      ...prev,
      [catId]: !prev[catId]
    }));
  };

  const handleInputChange = (accountId: number, month: number, rawValue: string) => {
    // Normalizar coma a punto decimal
    const value = rawValue.replace(',', '.');
    // Permitir vacío temporalmente mientras escribe, o números positivos con hasta 2 decimales
    if (value === '' || /^[0-9]*\.?[0-9]{0,2}$/.test(value)) {
      onCellChange(accountId, month, value);
    }
  };

  const handleBlur = (accountId: number, month: number, value: string) => {
    // Si queda vacío o no es número, restablecer a 0.00
    const cents = Math.max(0, parseToCents(value));
    const formatted = (cents / 100).toFixed(2);
    if (month === 1 && onReplicateJanuary) {
      onReplicateJanuary(accountId, formatted);
    } else {
      onCellChange(accountId, month, formatted);
    }
  };

  return (
    <div className="relative pb-24">
      {/* Contenedor de la tabla con scroll horizontal suave */}
      <div className="overflow-x-auto shadow-sm rounded-xl border border-slate-200 bg-white">
        <table className="w-full text-left border-collapse text-sm">
          
          {/* Encabezado Principal */}
          <thead className="bg-slate-100 text-slate-700 sticky top-16 z-20 shadow-[0_1px_3px_rgba(0,0,0,0.05)] font-semibold text-sm">
            <tr>
              <th className="py-3 px-3 w-[180px] min-w-[160px] border-r border-slate-200 text-slate-800">
                Proveedor
              </th>
              <th className="py-3 px-3 min-w-[280px] border-r border-slate-200">
                Categoría / Cuenta
              </th>
              {MONTH_NAMES.map((name, idx) => {
                const isJan = idx === 0;
                return (
                  <th
                    key={name}
                    className={`py-2.5 px-2 text-right min-w-[105px] border-r border-slate-200 transition-colors ${
                      isJan ? 'bg-indigo-50/90 text-indigo-950 font-bold border-b-2 border-indigo-400' : ''
                    }`}
                    title={isJan ? "Enero: Al colocar o modificar este valor se replica a todo el año (Feb-Dic)" : `${name}: Modificación individual`}
                  >
                    <div className="flex items-center justify-end space-x-1">
                      <span className="block">{name.slice(0, 3)}</span>
                      {isJan && (
                        <span className="text-[10px] bg-indigo-600 text-white font-bold px-1 rounded shadow-xs" title="Replicador automático">
                          ⇶
                        </span>
                      )}
                    </div>
                    <div className={`text-xs ${isJan ? 'text-indigo-600 font-semibold' : 'text-slate-400 font-normal'}`}>
                      {isJan ? 'Replica 1-12' : `Mes ${idx + 1}`}
                    </div>
                  </th>
                );
              })}
              <th className="py-3 px-3 text-right min-w-[130px] bg-slate-200/80 text-slate-900 font-bold">
                Total Anual
              </th>
            </tr>
          </thead>

          <tbody className="divide-y divide-slate-100 font-mono text-sm">
            {matrix.categories.map((category) => {
              const isCollapsed = !!collapsedCategories[category.id];

              return (
                <React.Fragment key={category.id}>
                  {/* Fila de Categoría (Agrupador) */}
                  <tr className="bg-slate-50/90 hover:bg-slate-100/90 font-sans transition-colors border-t-2 border-slate-200">
                    <td className="py-2.5 px-3 border-r border-slate-200 text-slate-400 text-xs italic">
                      —
                    </td>
                    <td className="py-2.5 px-3 border-r border-slate-200">
                      <button
                        onClick={() => toggleCategory(category.id)}
                        className="flex items-center space-x-2 text-left w-full group focus:outline-none"
                      >
                        <span className="text-slate-400 group-hover:text-indigo-600 transition-transform duration-200">
                          {isCollapsed ? '▶' : '▼'}
                        </span>
                        <span className="font-bold text-slate-800 text-sm tracking-wide">
                          {category.name}
                        </span>
                        <span className="text-xs text-slate-400 font-normal bg-white px-1.5 py-0.5 rounded border border-slate-200">
                          {category.code}
                        </span>
                        <span className="text-xs text-slate-400 font-normal">
                          ({category.accounts.length} cuentas)
                        </span>
                      </button>
                    </td>

                    {/* Totales Mensuales de la Categoría */}
                    {Array.from({ length: 12 }, (_, i) => i + 1).map(m => (
                      <td key={m} className="py-2.5 px-2 text-right border-r border-slate-200 font-semibold text-slate-800 text-sm">
                        {formatCurrencyDisplay(category.monthly_totals[m] || '0.00')}
                      </td>
                    ))}

                    {/* Total Anual de la Categoría */}
                    <td className="py-2.5 px-3 text-right bg-slate-100/80 font-bold text-indigo-900 text-sm">
                      {formatCurrencyDisplay(category.annual_total || '0.00')}
                    </td>
                  </tr>

                  {/* Cuentas de la Categoría */}
                  {!isCollapsed && category.accounts.map((account) => (
                    <tr key={account.id} className="hover:bg-indigo-50/40 transition-colors group">
                      
                      {/* Proveedor (Columna a la izquierda) */}
                      <td className="py-2 px-3 border-r border-slate-200 text-sm font-sans truncate text-slate-600" title={account.provider || ''}>
                        {account.provider ? (
                          <span className="inline-block bg-slate-100 text-slate-700 px-2 py-0.5 rounded text-xs border border-slate-200">
                            {account.provider}
                          </span>
                        ) : (
                          <span className="text-slate-300 italic text-xs">—</span>
                        )}
                      </td>

                      {/* Nombre y Código de Cuenta */}
                      <td className="py-2 px-3 pl-6 border-r border-slate-200 font-sans">
                        <div className="flex flex-col">
                          <span className="font-medium text-slate-800 text-sm">
                            • {account.name}
                          </span>
                          {account.code && (
                            <span className="text-xs text-slate-400">
                              Cod: {account.code}
                            </span>
                          )}
                        </div>
                      </td>

                      {/* 12 Meses Editables */}
                      {Array.from({ length: 12 }, (_, i) => i + 1).map(m => {
                        const isJan = m === 1;
                        return (
                          <td
                            key={m}
                            className={`p-0 border-r border-slate-200 ${
                              isJan ? 'bg-indigo-50/25' : ''
                            }`}
                          >
                            <input
                              type="text"
                              value={account.months[m] ?? '0.00'}
                              onFocus={(e) => (e.target as HTMLInputElement).select()}
                              onChange={(e) => handleInputChange(account.id, m, e.target.value)}
                              onBlur={(e) => handleBlur(account.id, m, e.target.value)}
                              onKeyDown={(e) => {
                                if (e.key === 'Enter') (e.target as HTMLInputElement).blur();
                              }}
                              title={
                                isJan
                                  ? 'Enero: Al ingresar o cambiar este valor se replica a todo el año (Feb-Dic). Presiona Enter o Tab al terminar.'
                                  : `${MONTH_NAMES[m - 1]}: Modificación individual para este mes`
                              }
                              aria-label={`${account.name} - ${MONTH_NAMES[m - 1]}`}
                              className={`w-full h-9 px-2 text-right bg-transparent text-slate-900 focus:bg-white focus:outline-none focus:ring-1 focus:ring-indigo-500 font-mono text-sm hover:bg-slate-50/60 ${
                                isJan ? 'font-semibold text-indigo-950' : ''
                              }`}
                            />
                          </td>
                        );
                      })}

                      {/* Total Anual de la Cuenta */}
                      <td className="py-2 px-3 text-right font-bold text-slate-800 bg-slate-50/50 text-sm">
                        {formatCurrencyDisplay(account.annual_total || '0.00')}
                      </td>
                    </tr>
                  ))}
                </React.Fragment>
              );
            })}
          </tbody>

          {/* Pie de Tabla con Totales Generales (Sticky al pie) */}
          <tfoot className="bg-slate-900 text-white font-mono sticky bottom-0 z-20 shadow-lg text-sm">
            <tr>
              <td className="py-3.5 px-3 border-r border-slate-700 font-sans font-bold text-sm uppercase tracking-wider text-slate-300">
                TOTAL GENERAL
              </td>
              <td className="py-3.5 px-3 border-r border-slate-700 font-sans font-bold text-sm">
                <div className="flex items-center justify-between">
                  <span>Consolidado</span>
                  {matrix.is_balanced ? (
                    <span className="text-xs text-emerald-400 font-semibold bg-emerald-950 px-2 py-0.5 rounded border border-emerald-800">
                      ✓ Cuadre Verificado
                    </span>
                  ) : (
                    <span className="text-xs text-rose-400 font-semibold bg-rose-950 px-2 py-0.5 rounded border border-rose-800">
                      ⚠ Descuadre
                    </span>
                  )}
                </div>
              </td>
              {Array.from({ length: 12 }, (_, i) => i + 1).map(m => (
                <td key={m} className="py-3.5 px-2 text-right border-r border-slate-700 font-bold text-amber-300 text-sm">
                  {formatCurrencyDisplay(matrix.general_monthly_totals[m] || '0.00')}
                </td>
              ))}
              <td className="py-3.5 px-3 text-right font-bold text-emerald-400 bg-slate-950 text-base">
                {formatCurrencyDisplay(matrix.general_annual_total || '0.00')}
              </td>
            </tr>
          </tfoot>

        </table>
      </div>

      {/* Barra Flotante de Guardado con Campos de Auditoría */}
      {pendingChangesCount > 0 && (
        <div className="fixed bottom-4 left-1/2 transform -translate-x-1/2 z-40 bg-slate-900 text-white px-5 py-3.5 rounded-xl shadow-2xl border border-slate-700 flex items-center space-x-4 animate-bounce-subtle">
          <div className="flex items-center space-x-2">
            <span className="w-2.5 h-2.5 rounded-full bg-amber-400 animate-pulse" />
            <span className="text-xs font-semibold text-amber-300">
              {pendingChangesCount} cambio(s) pendiente(s)
            </span>
          </div>

          <div className="h-4 w-px bg-slate-700" />

          {/* Campo Usuario para Auditoría */}
          <div className="flex items-center space-x-1.5">
            <label className="text-[11px] text-slate-400">Usuario:</label>
            <input
              type="text"
              value={modifiedBy}
              onChange={(e) => setModifiedBy(e.target.value)}
              placeholder="Identificador usuario"
              className="bg-slate-800 text-white text-xs px-2.5 py-1 rounded border border-slate-600 focus:outline-none focus:ring-1 focus:ring-indigo-400 w-28"
            />
          </div>

          {/* Campo Motivo para Auditoría */}
          <div className="flex items-center space-x-1.5">
            <label className="text-[11px] text-slate-400">Motivo:</label>
            <input
              type="text"
              value={reason}
              onChange={(e) => setReason(e.target.value)}
              placeholder="Ej. Ajuste de contrato"
              className="bg-slate-800 text-white text-xs px-2.5 py-1 rounded border border-slate-600 focus:outline-none focus:ring-1 focus:ring-indigo-400 w-48"
            />
          </div>

          <div className="flex items-center space-x-2">
            <button
              onClick={() => onSave(modifiedBy, reason)}
              disabled={isSaving}
              className="bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-semibold px-4 py-1.5 rounded-lg shadow transition disabled:opacity-50"
            >
              {isSaving ? 'Guardando...' : 'Guardar y Auditar'}
            </button>
            <button
              onClick={onDiscard}
              disabled={isSaving}
              className="text-xs text-slate-400 hover:text-white px-2.5 py-1.5 transition"
            >
              Descartar
            </button>
          </div>
        </div>
      )}
    </div>
  );
};
