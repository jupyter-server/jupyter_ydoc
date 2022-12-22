/* -----------------------------------------------------------------------------
| Copyright (c) Jupyter Development Team.
| Distributed under the terms of the Modified BSD License.
|----------------------------------------------------------------------------*/

import type * as nbformat from '@jupyterlab/nbformat';
import { JSONExt, PartialJSONValue } from '@lumino/coreutils';
import { ISignal, Signal } from '@lumino/signaling';
import * as Y from 'yjs';
import type {
  Delta,
  IMapChange,
  ISharedCell,
  ISharedNotebook,
  NotebookChange,
  SharedCell
} from './api.js';

import { YDocument } from './ydocument';
import { YCellType, YBaseCell, createCell, createCellModelFromSharedType } from './ycell';

/**
 * Shared implementation of the Shared Document types.
 *
 * Shared cells can be inserted into a SharedNotebook.
 * Shared cells only start emitting events when they are connected to a SharedNotebook.
 *
 * "Standalone" cells must not be inserted into a (Shared)Notebook.
 * Standalone cells emit events immediately after they have been created, but they must not
 * be included into a (Shared)Notebook.
 */
export class YNotebook
  extends YDocument<NotebookChange>
  implements ISharedNotebook
{
  /**
   * Create a new notebook
   *
   * #### Notes
   * The document is empty and must be populated
   *
   * @param options
   */
  constructor(options: ISharedNotebook.IOptions = {}) {
    super();
    this._disableDocumentWideUndoRedo =
      options.disableDocumentWideUndoRedo ?? false;
    this.cells = this._ycells.toArray().map(ycell => {
      if (!this._ycellMapping.has(ycell)) {
        this._ycellMapping.set(
          ycell,
          createCellModelFromSharedType(ycell, { notebook: this })
        );
      }
      return this._ycellMapping.get(ycell) as YCellType;
    });

    this.undoManager.addToScope(this._ycells);
    this._ycells.observe(this._onYCellsChanged);
    this.ymeta.observe(this._onMetaChanged);
  }

  /**
   * YJS map for the notebook metadata
   */
  readonly ymeta: Y.Map<any> = this.ydoc.getMap('meta');
  /**
   * Cells list
   */
  readonly cells: YCellType[];

  /**
   * Wether the undo/redo logic should be
   * considered on the full document across all cells.
   *
   * Default: false
   */
  get disableDocumentWideUndoRedo(): boolean {
    return this._disableDocumentWideUndoRedo;
  }

  /**
   * Notebook metadata
   */
  get metadata(): nbformat.INotebookMetadata {
    return this.getMetadata();
  }
  set metadata(v: nbformat.INotebookMetadata) {
    this.setMetadata(v);
  }

  /**
   * Signal triggered when a metadata changes.
   */
  get metadataChanged(): ISignal<this, IMapChange> {
    return this._metadataChanged;
  }

  /**
   * nbformat major version
   */
  get nbformat(): number {
    return this.ymeta.get('nbformat');
  }
  set nbformat(value: number) {
    this.transact(() => {
      this.ymeta.set('nbformat', value);
    }, false);
  }

  /**
   * nbformat minor version
   */
  get nbformat_minor(): number {
    return this.ymeta.get('nbformat_minor');
  }
  set nbformat_minor(value: number) {
    this.transact(() => {
      this.ymeta.set('nbformat_minor', value);
    }, false);
  }

  /**
   * Dispose of the resources.
   */
  dispose(): void {
    if (this.isDisposed) {
      return;
    }
    this._ycells.unobserve(this._onYCellsChanged);
    this.ymeta.unobserve(this._onMetaChanged);
    super.dispose();
  }

  /**
   * Get a shared cell by index.
   *
   * @param index: Cell's position.
   *
   * @returns The requested shared cell.
   */
  getCell(index: number): YCellType {
    return this.cells[index];
  }

  /**
   * Add a shared cell at the notebook bottom.
   *
   * @param cell Cell to add.
   *
   * @returns The added cell.
   */
  addCell(cell: SharedCell.Cell): YBaseCell<nbformat.IBaseCellMetadata> {
    return this.insertCell(this._ycells.length, cell);
  }

  /**
   * Insert a shared cell into a specific position.
   *
   * @param index: Cell's position.
   * @param cell: Cell to insert.
   *
   * @returns The inserted cell.
   */
  insertCell(
    index: number,
    cell: SharedCell.Cell
  ): YBaseCell<nbformat.IBaseCellMetadata> {
    return this.insertCells(index, [cell])[0];
  }

  /**
   * Insert a list of shared cells into a specific position.
   *
   * @param index: Position to insert the cells.
   * @param cells: Array of shared cells to insert.
   *
   * @returns The inserted cells.
   */
  insertCells(
    index: number,
    cells: SharedCell.Cell[]
  ): YBaseCell<nbformat.IBaseCellMetadata>[] {
    const yCells = cells.map(c => {
      const cell = createCell(c, this);
      this._ycellMapping.set(cell.ymodel, cell);
      return cell;
    });

    this.transact(() => {
      this._ycells.insert(
        index,
        yCells.map(cell => cell.ymodel)
      );
    });

    yCells.forEach(c => {
      c.setUndoManager();
    });

    return yCells;
  }

  /**
   * Move a cell.
   *
   * @param fromIndex: Index of the cell to move.
   * @param toIndex: New position of the cell.
   */
  moveCell(fromIndex: number, toIndex: number): void {
    this.moveCells(fromIndex, toIndex);
  }

  /**
   * Move cells.
   *
   * @param fromIndex: Index of the first cells to move.
   * @param toIndex: New position of the first cell (in the current array).
   * @param n: Number of cells to move (default 1)
   */
  moveCells(fromIndex: number, toIndex: number, n = 1): void {
    // FIXME we need to use yjs move feature to preserve undo history
    const clones = new Array(n)
      .fill(true)
      .map((_, idx) => this.getCell(fromIndex + idx).toJSON());
    this.transact(() => {
      this._ycells.delete(fromIndex, n);
      this._ycells.insert(
        fromIndex > toIndex ? toIndex : toIndex - n + 1,
        clones.map(clone => createCell(clone, this).ymodel)
      );
    });
  }

  /**
   * Remove a cell.
   *
   * @param index: Index of the cell to remove.
   */
  deleteCell(index: number): void {
    this.deleteCellRange(index, index + 1);
  }

  /**
   * Remove a range of cells.
   *
   * @param from: The start index of the range to remove (inclusive).
   * @param to: The end index of the range to remove (exclusive).
   */
  deleteCellRange(from: number, to: number): void {
    // Cells will be removed from the mapping in the model event listener.
    this.transact(() => {
      this._ycells.delete(from, to - from);
    });
  }

  /**
   * Delete a metadata notebook.
   *
   * @param key The key to delete
   */
  deleteMetadata(key: string): void {
    if (typeof this.getMetadata(key) === 'undefined') {
      return;
    }

    const allMetadata = JSONExt.deepCopy(this.ymeta.get('metadata'));
    delete allMetadata[key];
    this.setMetadata(allMetadata);
  }

  /**
   * Returns some metadata associated with the notebook.
   *
   * If no `key` is provided, it will return all metadata.
   * Else it will return the value for that key.
   *
   * @param key Key to get from the metadata
   * @returns Notebook's metadata.
   */
  getMetadata(): nbformat.INotebookMetadata;
  getMetadata(key: string): PartialJSONValue | undefined;
  getMetadata(
    key?: string
  ): nbformat.INotebookMetadata | PartialJSONValue | undefined {
    const meta = this.ymeta.get('metadata') ?? {};

    if (typeof key === 'string') {
      const value = meta[key];
      return typeof value === 'undefined'
        ? undefined // undefined is converted to `{}` by `JSONExt.deepCopy`
        : JSONExt.deepCopy(meta[key]);
    } else {
      return JSONExt.deepCopy(meta);
    }
  }

  /**
   * Sets some metadata associated with the notebook.
   *
   * If only one argument is provided, it will override all notebook metadata.
   * Otherwise a single key will be set to a new value.
   *
   * @param metadata All Notebook's metadata or the key to set.
   * @param value New metadata value
   */
  setMetadata(metadata: nbformat.INotebookMetadata): void;
  setMetadata(metadata: string, value: PartialJSONValue): void;
  setMetadata(
    metadata: nbformat.INotebookMetadata | string,
    value?: PartialJSONValue
  ): void {
    if (typeof metadata === 'string') {
      if (typeof value === 'undefined') {
        throw new TypeError(
          `Metadata value for ${metadata} cannot be 'undefined'; use deleteMetadata.`
        );
      }

      if (JSONExt.deepEqual(this.getMetadata(metadata) ?? null, value)) {
        return;
      }

      const update: Partial<nbformat.INotebookMetadata> = {};
      update[metadata] = value;
      this.updateMetadata(update);
    } else {
      if (!JSONExt.deepEqual(this.metadata, metadata)) {
        this.ymeta.set('metadata', JSONExt.deepCopy(metadata));
      }
    }
  }

  /**
   * Updates the metadata associated with the notebook.
   *
   * @param value: Metadata's attribute to update.
   */
  updateMetadata(value: Partial<nbformat.INotebookMetadata>): void {
    // TODO: Maybe modify only attributes instead of replacing the whole metadata?
    this.ymeta.set('metadata', { ...this.getMetadata(), ...value });
  }

  /**
   * Override the notebook with a JSON-serialized document.
   *
   * @param value The notebook
   */
  fromJSON(value: nbformat.INotebookContent): void {
    this.transact(() => {
      this.nbformat = value.nbformat;
      this.nbformat_minor = value.nbformat_minor;

      const metadata = value.metadata;
      if (metadata['orig_nbformat'] !== undefined) {
        delete metadata['orig_nbformat'];
      }
      this.metadata = metadata;

      const useId = value.nbformat === 4 && value.nbformat_minor >= 5;
      const ycells = value.cells.map(cell => {
        if (!useId) {
          delete cell.id;
        }
        return cell;
      });
      this.insertCells(this.cells.length, ycells);
      this.deleteCellRange(0, this.cells.length);
    });
  }

  /**
   * Serialize the model to JSON.
   */
  toJSON(): nbformat.INotebookContent {
    // strip cell ids if we have notebook format 4.0-4.4
    const pruneCellId = this.nbformat === 4 && this.nbformat_minor <= 4;

    return {
      metadata: this.metadata,
      nbformat_minor: this.nbformat_minor,
      nbformat: this.nbformat,
      cells: this.cells.map(c => {
        const raw = c.toJSON();
        if (pruneCellId) {
          delete raw.id;
        }
        return raw;
      })
    };
  }

  /**
   * Handle a change to the ystate.
   */
  private _onMetaChanged = (event: Y.YMapEvent<any>) => {
    if (event.keysChanged.has('metadata')) {
      const change = event.changes.keys.get('metadata');
      const metadataChange = {
        oldValue: change?.oldValue ? change!.oldValue : undefined,
        newValue: this.getMetadata()
      };

      const oldValue = metadataChange.oldValue ?? {};
      const oldKeys = Object.keys(oldValue);
      const newKeys = Object.keys(metadataChange.newValue);
      for (let key of new Set(oldKeys.concat(newKeys))) {
        if (!oldKeys.includes(key)) {
          this._metadataChanged.emit({
            key,
            newValue: metadataChange.newValue[key],
            type: 'add'
          });
        } else if (!newKeys.includes(key)) {
          this._metadataChanged.emit({
            key,
            oldValue: metadataChange.oldValue[key],
            type: 'remove'
          });
        } else if (
          !JSONExt.deepEqual(oldValue[key], metadataChange.newValue[key]!)
        ) {
          this._metadataChanged.emit({
            key,
            newValue: metadataChange.newValue[key],
            oldValue: metadataChange.oldValue[key],
            type: 'change'
          });
        }
      }

      this._changed.emit({ metadataChange });
    }

    if (event.keysChanged.has('nbformat')) {
      const change = event.changes.keys.get('nbformat');
      const nbformatChanged = {
        key: 'nbformat',
        oldValue: change?.oldValue ? change!.oldValue : undefined,
        newValue: this.nbformat
      };
      this._changed.emit({ nbformatChanged });
    }

    if (event.keysChanged.has('nbformat_minor')) {
      const change = event.changes.keys.get('nbformat_minor');
      const nbformatChanged = {
        key: 'nbformat_minor',
        oldValue: change?.oldValue ? change!.oldValue : undefined,
        newValue: this.nbformat_minor
      };
      this._changed.emit({ nbformatChanged });
    }
  };

  /**
   * Handle a change to the list of cells.
   */
  private _onYCellsChanged = (event: Y.YArrayEvent<Y.Map<any>>) => {
    // update the type cell mapping by iterating through the added/removed types
    event.changes.added.forEach(item => {
      const type = (item.content as Y.ContentType).type as Y.Map<any>;
      if (!this._ycellMapping.has(type)) {
        const c = createCellModelFromSharedType(type, { notebook: this });
        c!.setUndoManager();
        this._ycellMapping.set(type, c);
      }
    });
    event.changes.deleted.forEach(item => {
      const type = (item.content as Y.ContentType).type as Y.Map<any>;
      const model = this._ycellMapping.get(type);
      if (model) {
        model.dispose();
        this._ycellMapping.delete(type);
      }
    });
    let index = 0;

    // this reflects the event.changes.delta, but replaces the content of delta.insert with ycells
    const cellsChange: Delta<ISharedCell[]> = [];
    event.changes.delta.forEach((d: any) => {
      if (d.insert != null) {
        const insertedCells = d.insert.map((ycell: Y.Map<any>) =>
          this._ycellMapping.get(ycell)
        );
        cellsChange.push({ insert: insertedCells });
        this.cells.splice(index, 0, ...insertedCells);

        index += d.insert.length;
      } else if (d.delete != null) {
        cellsChange.push(d);
        this.cells.splice(index, d.delete);
      } else if (d.retain != null) {
        cellsChange.push(d);
        index += d.retain;
      }
    });

    this._changed.emit({
      cellsChange: cellsChange
    });
  };

  protected _metadataChanged = new Signal<this, IMapChange>(this);
  /**
   * Internal Yjs cells list
   */
  protected readonly _ycells: Y.Array<Y.Map<any>> = this.ydoc.getArray('cells');

  private _disableDocumentWideUndoRedo: boolean;
  private _ycellMapping: WeakMap<Y.Map<any>, YCellType> = new WeakMap();
}
