import React, { useEffect, useState, useCallback } from 'react';
import { BudgetMatrix, BudgetYear, ProjectionUpdate } from './types/budget';
import { recalculateMatrixLocally } from './utils/math';
import { Navbar } from './components/Navbar';
import { BudgetGrid } from './components/BudgetGrid';
import { AuditModal } from './components/AuditModal';
import { CategoryModal } from './components/CategoryModal';
import { AccountModal } from './components/AccountModal';
import { YearModal } from './components/YearModal';

export const App: React.FC = () => {
  const [years, setYears] = useState<BudgetYear[]>([]);
  const [selectedYear, setSelectedYear] = useState<number>(2026);
  const [matrix, setMatrix] = useState<BudgetMatrix | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  // Registro de cambios pendientes en memoria: key = "accountId-month"
  const [modifiedCells, setModifiedCells] = useState<Map<string, { accountId: number; month: number; amount: string }>>(new Map());
  const [isSaving, setIsSaving] = useState<boolean>(false);
  const [toastMessage, setToastMessage] = useState<string | null>(null);

  // Modales
  const [isAuditOpen, setIsAuditOpen] = useState(false);
  const [isCategoryOpen, setIsCategoryOpen] = useState(false);
  const [isAccountOpen, setIsAccountOpen] = useState(false);
  const [isYearOpen, setIsYearOpen] = useState(false);

  const showToast = (msg: string) => {
    setToastMessage(msg);
    setTimeout(() => setToastMessage(null), 4000);
  };

  const loadYears = async () => {
    try {
      const res = await fetch('/api/v1/years');
      if (res.ok) {
        const data: BudgetYear[] = await res.json();
        setYears(data);
        if (data.length > 0 && !data.some(y => y.year === selectedYear)) {
          setSelectedYear(data[0].year);
        }
      }
    } catch (err: any) {
      console.error("Error al cargar años:", err);
    }
  };

  const loadMatrix = useCallback(async (year: number) => {
    setLoading(true);
    setError(null);
    try {
      const res = await fetch(`/api/v1/budgets/${year}/matrix`);
      if (!res.ok) {
        throw new Error(`Error ${res.status}: No se pudo cargar la matriz para ${year}`);
      }
      const data: BudgetMatrix = await res.json();
      setMatrix(data);
      setModifiedCells(new Map());
    } catch (err: any) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadYears();
  }, []);

  useEffect(() => {
    if (selectedYear) {
      loadMatrix(selectedYear);
    }
  }, [selectedYear, loadMatrix]);

  // Edición reactiva en frontend
  const handleCellChange = (accountId: number, month: number, newAmount: string) => {
    if (!matrix) return;

    // 1. Clonar y actualizar el valor en la celda
    const updatedMatrix: BudgetMatrix = JSON.parse(JSON.stringify(matrix));
    for (const cat of updatedMatrix.categories) {
      const acc = cat.accounts.find(a => a.id === accountId);
      if (acc) {
        acc.months[month] = newAmount;
        break;
      }
    }

    // 2. Ejecutar las 6 reglas de cálculo en el cliente para retroalimentación instantánea
    const recalculated = recalculateMatrixLocally(updatedMatrix);
    setMatrix(recalculated);

    // 3. Registrar celda modificada para el guardado por lote
    const cellKey = `${accountId}-${month}`;
    setModifiedCells(prev => {
      const next = new Map(prev);
      next.set(cellKey, { accountId, month, amount: newAmount });
      return next;
    });
  };

  // Replicar valor de Enero a todos los meses (1..12) de la cuenta
  const handleReplicateJanuary = (accountId: number, formattedAmount: string) => {
    if (!matrix) return;

    const updatedMatrix: BudgetMatrix = JSON.parse(JSON.stringify(matrix));
    let accountName = '';
    for (const cat of updatedMatrix.categories) {
      const acc = cat.accounts.find(a => a.id === accountId);
      if (acc) {
        accountName = acc.name;
        for (let m = 1; m <= 12; m++) {
          acc.months[m] = formattedAmount;
        }
        break;
      }
    }

    const recalculated = recalculateMatrixLocally(updatedMatrix);
    setMatrix(recalculated);

    setModifiedCells(prev => {
      const next = new Map(prev);
      for (let m = 1; m <= 12; m++) {
        const cellKey = `${accountId}-${m}`;
        next.set(cellKey, { accountId, month: m, amount: formattedAmount });
      }
      return next;
    });

    showToast(`Enero ($${formattedAmount}) replicado a Feb - Dic en "${accountName}". Puedes ajustar los otros meses.`);
  };

  const handleSave = async (modifiedBy: string, reason: string) => {
    if (modifiedCells.size === 0 || !matrix) return;

    setIsSaving(true);
    try {
      const updates: ProjectionUpdate[] = Array.from(modifiedCells.values());
      const payload = {
        modified_by: modifiedBy.trim() || 'amoreno',
        reason: reason.trim() || 'Ajuste presupuestario',
        updates: updates
      };

      const res = await fetch(`/api/v1/budgets/${selectedYear}/projections`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      });

      if (!res.ok) {
        const errData = await res.json();
        throw new Error(errData.detail || "Error al guardar proyecciones");
      }

      const recalculatedMatrix: BudgetMatrix = await res.json();
      setMatrix(recalculatedMatrix);
      setModifiedCells(new Map());
      showToast(`¡Se guardaron y auditaron ${updates.length} cambio(s) exitosamente!`);
    } catch (err: any) {
      alert(`Error al guardar: ${err.message}`);
    } finally {
      setIsSaving(false);
    }
  };

  const handleDiscard = () => {
    if (window.confirm("¿Deseas descartar todas las modificaciones no guardadas?")) {
      loadMatrix(selectedYear);
    }
  };

  const handleChangeStatus = async (newStatus: string) => {
    try {
      const res = await fetch(`/api/v1/budgets/${selectedYear}/status?new_status=${newStatus}`, {
        method: 'PUT'
      });
      if (res.ok) {
        showToast(`Estado del año ${selectedYear} actualizado a ${newStatus}`);
        loadYears();
        loadMatrix(selectedYear);
      }
    } catch (err) {
      console.error("Error al actualizar estado:", err);
    }
  };

  return (
    <div className="min-h-screen bg-slate-50 flex flex-col">
      {/* Toast Notification */}
      {toastMessage && (
        <div className="fixed top-20 right-6 z-50 bg-emerald-700 text-white text-xs font-semibold px-4 py-3 rounded-xl shadow-xl flex items-center space-x-2 animate-fade-in">
          <span>✓</span>
          <span>{toastMessage}</span>
        </div>
      )}

      {/* Navbar Superior */}
      <Navbar
        years={years}
        selectedYear={selectedYear}
        onSelectYear={(y) => {
          if (modifiedCells.size > 0) {
            if (!window.confirm("Tienes cambios sin guardar. ¿Deseas cambiar de año y descartar?")) {
              return;
            }
          }
          setSelectedYear(y);
        }}
        currentStatus={matrix?.status || 'DRAFT'}
        onChangeStatus={handleChangeStatus}
        onOpenAudit={() => setIsAuditOpen(true)}
        onOpenNewCategory={() => setIsCategoryOpen(true)}
        onOpenNewAccount={() => setIsAccountOpen(true)}
        onOpenNewYear={() => setIsYearOpen(true)}
      />

      {/* Área Principal de Contenido */}
      <main className="flex-1 max-w-[1920px] w-full mx-auto px-4 sm:px-6 lg:px-8 py-5">
        
        {/* Cabecera Informativa del Año */}
        {matrix && (
          <div className="mb-4 bg-white p-4 rounded-xl border border-slate-200 shadow-sm flex flex-wrap items-center justify-between gap-3 text-xs">
            <div className="flex items-center space-x-4">
              <div>
                <span className="text-slate-400 font-medium">Año Fiscal:</span>{' '}
                <span className="font-bold text-slate-800 text-sm">{matrix.year}</span>
              </div>
              <div className="h-4 w-px bg-slate-200" />
              <div>
                <span className="text-slate-400 font-medium">Categorías:</span>{' '}
                <span className="font-semibold text-slate-700">{matrix.categories.length}</span>
              </div>
              <div className="h-4 w-px bg-slate-200" />
              <div>
                <span className="text-slate-400 font-medium">Cuentas Activas:</span>{' '}
                <span className="font-semibold text-slate-700">
                  {matrix.categories.reduce((acc, c) => acc + c.accounts.length, 0)}
                </span>
              </div>
              {matrix.notes && (
                <>
                  <div className="h-4 w-px bg-slate-200" />
                  <div className="text-slate-500 italic truncate max-w-md">
                    "{matrix.notes}"
                  </div>
                </>
              )}
            </div>

            <div className="flex items-center space-x-3">
              <span className="text-slate-500 text-xs">
                Total Anual Proyectado:
              </span>
              <span className="text-base font-extrabold text-indigo-700 font-mono">
                ${Number(matrix.general_annual_total).toLocaleString('es-EC', { minimumFractionDigits: 2 })}
              </span>
            </div>
          </div>
        )}

        {/* Mensaje de Error */}
        {error && (
          <div className="mb-5 bg-rose-50 border border-rose-200 text-rose-700 p-4 rounded-xl text-xs font-medium">
            {error}
          </div>
        )}

        {/* Loading Spinner */}
        {loading && (
          <div className="py-24 text-center">
            <div className="inline-block animate-spin rounded-full h-8 w-8 border-4 border-indigo-600 border-t-transparent" />
            <p className="mt-3 text-slate-500 text-xs font-medium">Calculando y cargando matriz presupuestaria...</p>
          </div>
        )}

        {/* Matriz Presupuestaria Principal */}
        {!loading && matrix && (
          <BudgetGrid
            matrix={matrix}
            onCellChange={handleCellChange}
            onReplicateJanuary={handleReplicateJanuary}
            pendingChangesCount={modifiedCells.size}
            onSave={handleSave}
            onDiscard={handleDiscard}
            isSaving={isSaving}
            userDefault="amoreno"
          />
        )}
      </main>

      {/* Modales */}
      <AuditModal
        year={selectedYear}
        isOpen={isAuditOpen}
        onClose={() => setIsAuditOpen(false)}
      />

      <CategoryModal
        isOpen={isCategoryOpen}
        onClose={() => setIsCategoryOpen(false)}
        onCreated={() => {
          showToast("Categoría creada con éxito");
          loadMatrix(selectedYear);
        }}
      />

      <AccountModal
        categories={matrix?.categories || []}
        isOpen={isAccountOpen}
        onClose={() => setIsAccountOpen(false)}
        onCreated={() => {
          showToast("Cuenta presupuestaria creada con éxito");
          loadMatrix(selectedYear);
        }}
      />

      <YearModal
        existingYears={years}
        isOpen={isYearOpen}
        onClose={() => setIsYearOpen(false)}
        onCreated={(newYear) => {
          showToast(`Año fiscal ${newYear} creado correctamente`);
          loadYears();
          setSelectedYear(newYear);
        }}
      />
    </div>
  );
};
