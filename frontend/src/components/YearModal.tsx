import React, { useState } from 'react';
import { BudgetYear } from '../types/budget';

interface YearModalProps {
  existingYears: BudgetYear[];
  isOpen: boolean;
  onClose: () => void;
  onCreated: (year: number) => void;
}

export const YearModal: React.FC<YearModalProps> = ({ existingYears, isOpen, onClose, onCreated }) => {
  const currentMaxYear = existingYears.length > 0 
    ? Math.max(...existingYears.map(y => y.year)) 
    : 2026;
  const [year, setYear] = useState<number>(currentMaxYear + 1);
  const [notes, setNotes] = useState('');
  const [copyFromYear, setCopyFromYear] = useState<string>('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  if (!isOpen) return null;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!year || year < 2000 || year > 2100) {
      setError("Ingrese un año válido entre 2000 y 2100");
      return;
    }

    setLoading(true);
    setError('');
    try {
      const res = await fetch('/api/v1/years', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          year: Number(year),
          notes: notes.trim(),
          copy_from_year: copyFromYear ? Number(copyFromYear) : null
        })
      });

      if (!res.ok) {
        const data = await res.json();
        throw new Error(data.detail || "Error al crear el año presupuestario");
      }

      onCreated(Number(year));
      onClose();
    } catch (err: any) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/60 backdrop-blur-sm p-4">
      <div className="bg-white rounded-2xl shadow-2xl w-full max-w-md overflow-hidden border border-slate-200">
        
        <div className="px-6 py-4 border-b border-slate-200 bg-slate-50 flex items-center justify-between">
          <h3 className="text-sm font-bold text-slate-800">Crear Nuevo Año Presupuestario</h3>
          <button onClick={onClose} className="text-slate-400 hover:text-slate-600 font-bold">✕</button>
        </div>

        <form onSubmit={handleSubmit} className="p-6 space-y-4 text-xs">
          {error && (
            <div className="bg-rose-50 text-rose-700 p-2.5 rounded-lg border border-rose-200 font-medium">
              {error}
            </div>
          )}

          <div>
            <label className="block font-semibold text-slate-700 mb-1">Año Fiscal</label>
            <input
              type="number"
              value={year}
              onChange={(e) => setYear(Number(e.target.value))}
              min={2000}
              max={2100}
              className="w-full bg-slate-50 border border-slate-300 rounded-lg px-3 py-2 text-slate-800 focus:outline-none focus:ring-2 focus:ring-indigo-500 font-bold text-sm"
              required
            />
          </div>

          <div>
            <label className="block font-semibold text-slate-700 mb-1">Clonar Proyecciones de Año Previo (Opcional)</label>
            <select
              value={copyFromYear}
              onChange={(e) => setCopyFromYear(e.target.value)}
              aria-label="Seleccionar año previo para clonar proyecciones"
              className="w-full bg-slate-50 border border-slate-300 rounded-lg px-3 py-2 text-slate-800 focus:outline-none focus:ring-2 focus:ring-indigo-500"
            >
              <option value="">Iniciar con importes en $0.00</option>
              {existingYears.map(y => (
                <option key={y.year} value={y.year}>Copiar valores desde {y.year}</option>
              ))}
            </select>
            <p className="text-[10px] text-slate-400 mt-1">
              Permite prellenar los 12 meses tomando de base la estructura de otro año fiscal.
            </p>
          </div>

          <div>
            <label className="block font-semibold text-slate-700 mb-1">Notas / Premisas del Año</label>
            <textarea
              rows={3}
              placeholder="Ej. Premisas: Aumento de enlaces en 4 tiendas, migración a SDWAN..."
              value={notes}
              onChange={(e) => setNotes(e.target.value)}
              className="w-full bg-slate-50 border border-slate-300 rounded-lg px-3 py-2 text-slate-800 focus:outline-none focus:ring-2 focus:ring-indigo-500"
            />
          </div>

          <div className="pt-3 border-t border-slate-100 flex items-center justify-end space-x-2">
            <button
              type="button"
              onClick={onClose}
              className="px-3.5 py-1.5 rounded-lg text-slate-600 hover:bg-slate-100 font-medium transition"
            >
              Cancelar
            </button>
            <button
              type="submit"
              disabled={loading}
              className="px-4 py-1.5 rounded-lg bg-indigo-600 hover:bg-indigo-700 text-white font-semibold shadow transition disabled:opacity-50"
            >
              {loading ? 'Creando...' : 'Crear Año'}
            </button>
          </div>
        </form>

      </div>
    </div>
  );
};
