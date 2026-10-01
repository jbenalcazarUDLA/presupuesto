import React from 'react';
import { BudgetYear } from '../types/budget';

interface NavbarProps {
  years: BudgetYear[];
  selectedYear: number;
  onSelectYear: (year: number) => void;
  currentStatus: string;
  onChangeStatus: (status: string) => void;
  onOpenAudit: () => void;
  onOpenNewCategory: () => void;
  onOpenNewAccount: () => void;
  onOpenNewYear: () => void;
}

export const Navbar: React.FC<NavbarProps> = ({
  years,
  selectedYear,
  onSelectYear,
  currentStatus,
  onChangeStatus,
  onOpenAudit,
  onOpenNewCategory,
  onOpenNewAccount,
  onOpenNewYear
}) => {
  const getStatusBadge = (status: string) => {
    switch (status) {
      case 'APPROVED':
        return 'bg-emerald-100 text-emerald-800 border-emerald-300';
      case 'CLOSED':
        return 'bg-rose-100 text-rose-800 border-rose-300';
      default:
        return 'bg-amber-100 text-amber-800 border-amber-300';
    }
  };

  const getStatusLabel = (status: string) => {
    switch (status) {
      case 'APPROVED': return 'APROBADO';
      case 'CLOSED': return 'CERRADO';
      default: return 'BORRADOR';
    }
  };

  return (
    <header className="bg-white border-b border-slate-200 sticky top-0 z-30 shadow-sm">
      <div className="max-w-[1920px] mx-auto px-4 sm:px-6 lg:px-8 h-16 flex items-center justify-between">
        
        {/* Logo / Título */}
        <div className="flex items-center space-x-3">
          <div className="w-9 h-9 rounded-lg bg-indigo-600 flex items-center justify-center text-white font-bold shadow-md shadow-indigo-100">
            📊
          </div>
          <div>
            <h1 className="text-lg font-bold text-slate-900 leading-tight">Planificador Presupuestario</h1>
            <p className="text-xs text-slate-500 font-medium">Proyección Anual • Tecnología EDIMCA</p>
          </div>
        </div>

        {/* Selector de Año y Estado */}
        <div className="flex items-center space-x-3">
          <div className="flex items-center bg-slate-100 p-1 rounded-lg border border-slate-200">
            <span className="text-xs font-semibold text-slate-500 px-2">AÑO:</span>
            <select
              value={selectedYear}
              onChange={(e) => onSelectYear(Number(e.target.value))}
              aria-label="Seleccionar año presupuestario"
              className="bg-white text-sm font-bold text-indigo-700 rounded-md px-3 py-1 shadow-sm border border-slate-200 focus:outline-none focus:ring-2 focus:ring-indigo-500"
            >
              {years.map(y => (
                <option key={y.year} value={y.year}>{y.year}</option>
              ))}
            </select>
          </div>

          <div className="flex items-center space-x-1.5">
            <span
              className={`text-xs px-2.5 py-1 rounded-full border font-semibold tracking-wider ${getStatusBadge(currentStatus)}`}
            >
              {getStatusLabel(currentStatus)}
            </span>
            <select
              value={currentStatus}
              onChange={(e) => onChangeStatus(e.target.value)}
              aria-label="Cambiar estado del presupuesto"
              className="text-xs bg-slate-50 border border-slate-200 text-slate-600 rounded px-1.5 py-1 hover:bg-slate-100 focus:outline-none cursor-pointer"
            >
              <option value="DRAFT">Borrador</option>
              <option value="APPROVED">Aprobar</option>
              <option value="CLOSED">Cerrar</option>
            </select>
          </div>
        </div>

        {/* Acciones Rápidas */}
        <div className="flex items-center space-x-2">
          <button
            onClick={onOpenAudit}
            className="flex items-center space-x-1.5 text-xs font-medium text-slate-700 bg-slate-100 hover:bg-slate-200 px-3 py-1.5 rounded-md border border-slate-300 transition"
          >
            <span>📜</span>
            <span>Historial Auditoría</span>
          </button>

          <div className="h-4 w-px bg-slate-200 mx-1" />

          <button
            onClick={onOpenNewAccount}
            className="text-xs font-medium text-indigo-700 bg-indigo-50 hover:bg-indigo-100 px-3 py-1.5 rounded-md border border-indigo-200 transition"
          >
            + Nueva Cuenta
          </button>

          <button
            onClick={onOpenNewCategory}
            className="text-xs font-medium text-indigo-700 bg-indigo-50 hover:bg-indigo-100 px-3 py-1.5 rounded-md border border-indigo-200 transition"
          >
            + Nueva Categoría
          </button>

          <button
            onClick={onOpenNewYear}
            className="text-xs font-medium text-white bg-indigo-600 hover:bg-indigo-700 px-3 py-1.5 rounded-md shadow-sm transition"
          >
            + Nuevo Año
          </button>
        </div>

      </div>
    </header>
  );
};
