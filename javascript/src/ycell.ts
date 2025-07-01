/* -----------------------------------------------------------------------------
| Copyright (c) Jupyter Development Team.
| Distributed under the terms of the Modified BSD License.
|----------------------------------------------------------------------------*/

import type * as nbformat from '@jupyterlab/nbformat';
import { JSONExt, JSONObject, PartialJSONValue, UUID } from '@lumino/coreutils';
import { ISignal, Signal } from '@lumino/signaling';
import { Awareness } from 'y-protocols/awareness';
import * as Y from 'yjs';
import type {
  CellChange,
  IExecutionState,
  IMapChange,
  ISharedAttachmentsCell,
  ISharedBaseCell,
  ISharedCodeCell,
  ISharedMarkdownCell,
  ISharedRawCell,
  SharedCell
} from './api.js';
import { IYText } from './ytext.js';
import { YNotebook } from './ynotebook.js';

/**
 * Cell type.
 */
export type YCellType = YRawCell | YCodeCell | YMarkdownCell;

/**
 * Create a new shared cell model given the YJS shared type.
 */
export const createCellModelFromSharedType = (
  type: Y.Map<any>,
  options: SharedCell.IOptions = {}
): YCellType => {
  switch (type.get('cell_type')) {
    case 'code':
      return new YCodeCell(
        type,
        type.get('source'),
        type.get('outputs'),
        options
      );
    case 'markdown':
      return new YMarkdownCell(type, type.get('source'), options);
    case 'raw':
      return new YRawCell(type, type.get('source'), options);
    default:
      throw new Error('Found unknown cell type');
  }
};

/**
 * Create a new cell that can be inserted in an existing shared model.
 *
 * If no notebook is specified the cell will be standalone.
 *
 * @param cell Cell JSON representation
 * @param notebook Notebook to which the cell will be added
 */
export const createCell = (
  cell: SharedCell.Cell,
  notebook?: YNotebook
): YCodeCell | YMarkdownCell | YRawCell => {
  const ymodel = new Y.Map();
  const ysource = new Y.Text();
  const ymetadata = new Y.Map();
  ymodel.set('source', ysource);
  ymodel.set('metadata', ymetadata);
  ymodel.set('cell_type', cell.cell_type);
  ymodel.set('id', cell.id ?? UUID.uuid4());

  let ycell: YCellType;
  switch (cell.cell_type) {
    case 'markdown': {
      ycell = new YMarkdownCell(ymodel, ysource, { notebook }, ymetadata);
      if (cell.attachments != null) {
        ycell.setAttachments(cell.attachments as nbformat.IAttachments);
      }
      break;
    }
    case 'code': {
      const youtputs = new Y.Array();
      ymodel.set('outputs', youtputs);
      ycell = new YCodeCell(
        ymodel,
        ysource,
        youtputs,
        {
          notebook
        },
        ymetadata
      );
      const cCell = cell as Partial<nbformat.ICodeCell>;
      ycell.execution_count = cCell.execution_count ?? null;
      if (cCell.outputs) {
        ycell.setOutputs(cCell.outputs);
      }
      break;
    }
    default: {
      // raw
      ycell = new YRawCell(ymodel, ysource, { notebook }, ymetadata);
      if (cell.attachments) {
        ycell.setAttachments(cell.attachments as nbformat.IAttachments);
      }
      break;
    }
  }

  if (cell.metadata != null) {
    ycell.setMetadata(cell.metadata);
  }
  if (cell.source != null) {
    ycell.setSource(
      typeof cell.source === 'string' ? cell.source : cell.source.join('')
    );
  }
  return ycell;
};

/**
 * Create a new cell that cannot be inserted in an existing shared model.
 *
 * @param cell Cell JSON representation
 */
export const createStandaloneCell = (cell: SharedCell.Cell): YCellType =>
  createCell(cell);

export class YBaseCell<Metadata extends nbformat.IBaseCellMetadata>
  implements ISharedBaseCell<Metadata>, IYText
{
  /**
   * Create a new YCell that works standalone. It cannot be
   * inserted into a YNotebook because the Yjs model is already
   * attached to an anonymous Y.Doc instance.
   */
  static create(id?: string): YBaseCell<any> {
    return createCell({ id, cell_type: this.prototype.cell_type });
  }

  /**
   * Base cell constructor
   *
   * ### Notes
   * Don't use the constructor directly - prefer using ``YNotebook.insertCell``
   *
   * The ``ysource`` is needed because ``ymodel.get('source')`` will
   * not return the real source if the model is not yet attached to
   * a document. Requesting it explicitly allows to introspect a non-empty
   * source before the cell is attached to the document.
   *
   * @param ymodel Cell map
   * @param ysource Cell source
   * @param options \{ notebook?: The notebook the cell is attached to \}
   * @param ymetadata Cell metadata
   */
  constructor(
    ymodel: Y.Map<any>,
    ysource: Y.Text,
    options: SharedCell.IOptions = {},
    ymetadata?: Y.Map<any>
  ) {
    this.ymodel = ymodel;
    this._ysource = ysource;
    this._ymetadata = ymetadata ?? this.ymodel.get('metadata');
    this._prevSourceLength = ysource ? ysource.length : 0;
    this._notebook = null;
    this._awareness = null;
    this._undoManager = null;
    if (options.notebook) {
      this._notebook = options.notebook as YNotebook;
      if (this._notebook.disableDocumentWideUndoRedo) {
        this._undoManager = new Y.UndoManager([this.ymodel], {
          trackedOrigins: new Set([this]),
          doc: this._notebook.ydoc
        });
      }
    } else {
      // Standalone cell
      const doc = new Y.Doc();
      doc.getArray().insert(0, [this.ymodel]);
      this._awareness = new Awareness(doc);
      this._undoManager = new Y.UndoManager([this.ymodel], {
        trackedOrigins: new Set([this])
      });
    }

    this.ymodel.observeDeep(this._modelObserver);
  }

  /**
   * Cell notebook awareness or null.
   */
  get awareness(): Awareness | null {
    return this._awareness ?? this.notebook?.awareness ?? null;
  }

  /**
   * The type of the cell.
   */
  get cell_type(): any {
    throw new Error('A YBaseCell must not be constructed');
  }

  /**
   * The changed signal.
   */
  get changed(): ISignal<this, CellChange> {
    return this._changed;
  }

  /**
   * Signal emitted when the cell is disposed.
   */
  get disposed(): ISignal<this, void> {
    return this._disposed;
  }

  /**
   * Cell id
   */
  get id(): string {
    return this.getId();
  }

  /**
   * Whether the model has been disposed or not.
   */
  get isDisposed(): boolean {
    return this._isDisposed;
  }

  /**
   * Whether the cell is standalone or not.
   *
   * If the cell is standalone. It cannot be
   * inserted into a YNotebook because the Yjs model is already
   * attached to an anonymous Y.Doc instance.
   */
  get isStandalone(): boolean {
    return this._notebook !== null;
  }

  /**
   * Cell metadata.
   *
   * #### Notes
   * You should prefer to access and modify the specific key of interest.
   */
  get metadata(): Partial<Metadata> {
    return this.getMetadata();
  }
  set metadata(v: Partial<Metadata>) {
    this.setMetadata(v);
  }

  /**
   * Signal triggered when the cell metadata changes.
   */
  get metadataChanged(): ISignal<this, IMapChange> {
    return this._metadataChanged;
  }

  /**
   * The notebook that this cell belongs to.
   */
  get notebook(): YNotebook | null {
    return this._notebook;
  }

  /**
   * Cell input content.
   */
  get source(): string {
    return this.getSource();
  }
  set source(v: string) {
    this.setSource(v);
  }

  /**
   * The cell undo manager.
   */
  get undoManager(): Y.UndoManager | null {
    if (!this.notebook) {
      return this._undoManager;
    }
    return this.notebook?.disableDocumentWideUndoRedo
      ? this._undoManager
      : this.notebook.undoManager;
  }

  readonly ymodel: Y.Map<any>;

  get ysource(): Y.Text {
    return this._ysource;
  }

  /**
   * Whether the object can undo changes.
   */
  canUndo(): boolean {
    return !!this.undoManager && this.undoManager.undoStack.length > 0;
  }

  /**
   * Whether the object can redo changes.
   */
  canRedo(): boolean {
    return !!this.undoManager && this.undoManager.redoStack.length > 0;
  }

  /**
   * Clear the change stack.
   */
  clearUndoHistory(): void {
    this.undoManager?.clear();
  }

  /**
   * Undo an operation.
   */
  undo(): void {
    this.undoManager?.undo();
  }

  /**
   * Redo an operation.
   */
  redo(): void {
    this.undoManager?.redo();
  }

  /**
   * Dispose of the resources.
   */
  dispose(): void {
    if (this._isDisposed) return;
    this._isDisposed = true;
    this.ymodel.unobserveDeep(this._modelObserver);

    if (this._awareness) {
      // A new document is created for standalone cell.
      const doc = this._awareness.doc;
      this._awareness.destroy();
      doc.destroy();
    }
    if (this._undoManager) {
      // Be sure to not destroy the document undo manager.
      if (this._undoManager === this.notebook?.undoManager) {
        this._undoManager = null;
      } else {
        this._undoManager.destroy();
      }
    }
    this._disposed.emit();
    Signal.clearData(this);
  }

  /**
   * Get cell id.
   *
   * @returns Cell id
   */
  getId(): string {
    return this.ymodel.get('id');
  }

  /**
   * Gets cell's source.
   *
   * @returns Cell's source.
   */
  getSource(): string {
    return this.ysource.toString();
  }

  /**
   * Sets cell's source.
   *
   * @param value: New source.
   */
  setSource(value: string): void {
    this.transact(() => {
      this.ysource.delete(0, this.ysource.length);
      this.ysource.insert(0, value);
    });
    // @todo Do we need proper replace semantic? This leads to issues in editor bindings because they don't switch source.
    // this.ymodel.set('source', new Y.Text(value));
  }

  /**
   * Replace content from `start' to `end` with `value`.
   *
   * @param start: The start index of the range to replace (inclusive).
   *
   * @param end: The end index of the range to replace (exclusive).
   *
   * @param value: New source (optional).
   */
  updateSource(start: number, end: number, value = ''): void {
    this.transact(() => {
      const ysource = this.ysource;
      // insert and then delete.
      // This ensures that the cursor position is adjusted after the replaced content.
      ysource.insert(start, value);
      ysource.delete(start + value.length, end - start);
    });
  }

  /**
   * Delete a metadata cell.
   *
   * @param key The key to delete
   */
  deleteMetadata(key: string): void {
    if (typeof this.getMetadata(key) === 'undefined') {
      return;
    }

    this.transact(() => {
      this._ymetadata.delete(key);

      const jupyter = this.getMetadata('jupyter') as any;
      if (key === 'collapsed' && jupyter) {
        // eslint-disable-next-line @typescript-eslint/no-unused-vars
        const { outputs_hidden, ...others } = jupyter;

        if (Object.keys(others).length === 0) {
          this._ymetadata.delete('jupyter');
        } else {
          this._ymetadata.set('jupyter', others);
        }
      } else if (key === 'jupyter') {
        this._ymetadata.delete('collapsed');
      }
    }, false);
  }

  /**
   * Returns all or a single metadata associated with the cell.
   *
   * @param key The metadata key
   * @returns cell's metadata.
   */
  getMetadata(): Partial<Metadata>;
  getMetadata(key: string): PartialJSONValue | undefined;
  getMetadata(key?: string): Partial<Metadata> | PartialJSONValue | undefined {
    const metadata = this._ymetadata;

    // Transiently the metadata can be missing - like during destruction
    if (metadata === undefined) {
      return undefined;
    }

    if (typeof key === 'string') {
      const value = metadata.get(key);
      return typeof value === 'undefined'
        ? undefined // undefined is converted to `{}` by `JSONExt.deepCopy`
        : JSONExt.deepCopy(metadata.get(key));
    } else {
      return JSONExt.deepCopy(metadata.toJSON());
    }
  }

  /**
   * Sets all or a single cell metadata.
   *
   * If only one argument is provided, it will override all cell metadata.
   * Otherwise a single key will be set to a new value.
   *
   * @param metadata Cell's metadata key or cell's metadata.
   * @param value Metadata value
   */
  setMetadata(metadata: Partial<Metadata>): void;
  setMetadata(metadata: string, value: PartialJSONValue): void;
  setMetadata(
    metadata: Partial<Metadata> | string,
    value?: PartialJSONValue
  ): void {
    if (typeof metadata === 'string') {
      if (typeof value === 'undefined') {
        throw new TypeError(
          `Metadata value for ${metadata} cannot be 'undefined'; use deleteMetadata.`
        );
      }
      const key = metadata;

      // Only set metadata if we change something to avoid infinite
      // loop of signal changes.
      if (JSONExt.deepEqual((this.getMetadata(key) as any) ?? null, value)) {
        return;
      }

      this.transact(() => {
        this._ymetadata.set(key, value);

        if (key === 'collapsed') {
          const jupyter = ((this.getMetadata('jupyter') as any) ?? {}) as any;
          if (jupyter.outputs_hidden !== value) {
            this.setMetadata('jupyter', {
              ...jupyter,
              outputs_hidden: value
            });
          }
        } else if (key === 'jupyter') {
          const isHidden = (value as JSONObject)['outputs_hidden'];
          if (typeof isHidden !== 'undefined') {
            if (this.getMetadata('collapsed') !== isHidden) {
              this.setMetadata('collapsed', isHidden);
            }
          } else {
            this.deleteMetadata('collapsed');
          }
        }
      }, false);
    } else {
      const clone = JSONExt.deepCopy(metadata) as any;
      if (clone.collapsed != null) {
        clone.jupyter = clone.jupyter || {};
        (clone as any).jupyter.outputs_hidden = clone.collapsed;
      } else if (clone?.jupyter?.outputs_hidden != null) {
        clone.collapsed = clone.jupyter.outputs_hidden;
      }
      if (!JSONExt.deepEqual(clone, this.getMetadata())) {
        this.transact(() => {
          for (const [key, value] of Object.entries(clone)) {
            this._ymetadata.set(key, value);
          }
        }, false);
      }
    }
  }

  /**
   * Serialize the model to JSON.
   */
  toJSON(): nbformat.IBaseCell {
    return {
      id: this.getId(),
      cell_type: this.cell_type,
      source: this.getSource(),
      metadata: this.getMetadata()
    };
  }

  /**
   * Perform a transaction. While the function f is called, all changes to the shared
   * document are bundled into a single event.
   *
   * @param f Transaction to execute
   * @param undoable Whether to track the change in the action history or not (default `true`)
   */
  transact(f: () => void, undoable = true, origin: any = null): void {
    !this.notebook || this.notebook.disableDocumentWideUndoRedo
      ? this.ymodel.doc == null
        ? f()
        : this.ymodel.doc.transact(f, undoable ? this : origin)
      : this.notebook.transact(f, undoable);
  }

  /**
   * Extract changes from YJS events
   *
   * @param events YJS events
   * @returns Cell changes
   */
  protected getChanges(events: Y.YEvent<any>[]): Partial<CellChange> {
    const changes: CellChange = {};

    const sourceEvent = events.find(
      event => event.target === this.ymodel.get('source')
    );
    if (sourceEvent) {
      changes.sourceChange = sourceEvent.changes.delta as any;
    }

    const metadataEvents = events.find(
      event => event.target === this._ymetadata
    );
    if (metadataEvents) {
      changes.metadataChange = metadataEvents.changes.keys;

      metadataEvents.changes.keys.forEach((change, key) => {
        switch (change.action) {
          case 'add':
            this._metadataChanged.emit({
              key,
              newValue: this._ymetadata.get(key),
              type: 'add'
            });
            break;
          case 'delete':
            this._metadataChanged.emit({
              key,
              oldValue: change.oldValue,
              type: 'remove'
            });
            break;
          case 'update':
            {
              const newValue = this._ymetadata.get(key);
              const oldValue = change.oldValue;
              let equal = true;
              if (typeof oldValue == 'object' && typeof newValue == 'object') {
                equal = JSONExt.deepEqual(oldValue, newValue);
              } else {
                equal = oldValue === newValue;
              }

              if (!equal) {
                this._metadataChanged.emit({
                  key,
                  type: 'change',
                  oldValue,
                  newValue
                });
              }
            }
            break;
        }
      });
    }

    const modelEvent = events.find(event => event.target === this.ymodel) as
      | undefined
      | Y.YMapEvent<any>;

    // The model allows us to replace the complete source with a new string. We express this in the Delta format
    // as a replace of the complete string.
    const ysource = this.ymodel.get('source');
    if (modelEvent && modelEvent.keysChanged.has('source')) {
      changes.sourceChange = [
        { delete: this._prevSourceLength },
        { insert: ysource.toString() }
      ];
    }
    this._prevSourceLength = ysource.length;

    return changes;
  }

  /**
   * Handle a change to the ymodel.
   */
  private _modelObserver = (
    events: Y.YEvent<any>[],
    transaction: Y.Transaction
  ) => {
    if (transaction.origin !== 'silent-change') {
      this._changed.emit(this.getChanges(events));
    }
  };

  protected _metadataChanged = new Signal<this, IMapChange>(this);
  /**
   * The notebook that this cell belongs to.
   */
  protected _notebook: YNotebook | null = null;
  private _awareness: Awareness | null;
  private _changed = new Signal<this, CellChange>(this);
  private _disposed = new Signal<this, void>(this);
  private _isDisposed = false;
  private _prevSourceLength: number;
  private _undoManager: Y.UndoManager | null = null;
  private _ymetadata: Y.Map<any>;
  private _ysource: Y.Text;
}

/**
 * Shareable code cell.
 */
export class YCodeCell
  extends YBaseCell<nbformat.IBaseCellMetadata>
  implements ISharedCodeCell
{
  /**
   * Create a new YCodeCell that works standalone. It cannot be
   * inserted into a YNotebook because the Yjs model is already
   * attached to an anonymous Y.Doc instance.
   */
  static create(id?: string): YCodeCell {
    return super.create(id) as YCodeCell;
  }

  /**
   * Code cell constructor
   *
   * ### Notes
   * Don't use the constructor directly - prefer using ``YNotebook.insertCell``
   *
   * The ``ysource`` is needed because ``ymodel.get('source')`` will
   * not return the real source if the model is not yet attached to
   * a document. Requesting it explicitly allows to introspect a non-empty
   * source before the cell is attached to the document.
   *
   * @param ymodel Cell map
   * @param ysource Cell source
   * @param youtputs Code cell outputs
   * @param options \{ notebook?: The notebook the cell is attached to \}
   * @param ymetadata Cell metadata
   */
  constructor(
    ymodel: Y.Map<any>,
    ysource: Y.Text,
    youtputs: Y.Array<any>,
    options: SharedCell.IOptions = {},
    ymetadata?: Y.Map<any>
  ) {
    super(ymodel, ysource, options, ymetadata);
    this._youtputs = youtputs;
  }

  /**
   * The type of the cell.
   */
  get cell_type(): 'code' {
    return 'code';
  }

  /**
   * The code cell's prompt number. Will be null if the cell has not been run.
   */
  get execution_count(): number | null {
    return this.ymodel.get('execution_count') || null;
  }
  set execution_count(count: number | null) {
    // Do not use `this.execution_count`. When initializing the
    // cell, we need to set execution_count to `null` if we compare
    // using `this.execution_count` it will return `null` and we will
    // never initialize it
    if (this.ymodel.get('execution_count') !== count) {
      this.transact(() => {
        this.ymodel.set('execution_count', count);
      }, false);
    }
  }

  /**
   * The code cell's execution state.
   */
  get executionState(): IExecutionState {
    return this.ymodel.get('execution_state') ?? 'idle';
  }
  set executionState(state: IExecutionState) {
    if (this.ymodel.get('execution_state') !== state) {
      this.transact(() => {
        this.ymodel.set('execution_state', state);
      }, false);
    }
  }

  /**
   * Cell outputs.
   */
  get outputs(): Array<nbformat.IOutput> {
    return this.getOutputs();
  }
  set outputs(v: Array<nbformat.IOutput>) {
    this.setOutputs(v);
  }
  get youtputs(): Y.Array<any> {
    return this._youtputs;
  }

  /**
   * Execution, display, or stream outputs.
   */
  getOutputs(): Array<nbformat.IOutput> {
    return JSONExt.deepCopy(this._youtputs.toJSON());
  }

  createOutputs(outputs: Array<nbformat.IOutput>): Array<Y.Map<any>> {
    const newOutputs: Array<Y.Map<any>> = [];
    for (const output of JSONExt.deepCopy(outputs)) {
      let _newOutput1: { [id: string]: any };
      if (output.output_type === 'stream') {
        // Set the text field as a Y.Text
        const { text, ...outputWithoutText } = output;
        _newOutput1 = outputWithoutText;
        const newText = new Y.Text();
        let _text = text instanceof Array ? text.join() : (text as string);
        newText.insert(0, _text);
        _newOutput1['text'] = newText;
      } else {
        _newOutput1 = output;
      }
      const _newOutput2: [string, any][] = [];
      for (const [key, value] of Object.entries(_newOutput1)) {
        _newOutput2.push([key, value]);
      }
      const newOutput = new Y.Map(_newOutput2);
      newOutputs.push(newOutput);
    }
    return newOutputs;
  }

  /**
   * Replace all outputs.
   */
  setOutputs(outputs: Array<nbformat.IOutput>): void {
    this.transact(() => {
      this._youtputs.delete(0, this._youtputs.length);
      const newOutputs = this.createOutputs(outputs);
      this._youtputs.insert(0, newOutputs);
    }, false);
  }

  /**
   * Remove text from a stream output.
   */
  removeStreamOutput(index: number, start: number, origin: any = null): void {
    this.transact(
      () => {
        const output = this._youtputs.get(index);
        const prevText = output.get('text') as Y.Text;
        const length = prevText.length - start;
        prevText.delete(start, length);
      },
      false,
      origin
    );
  }

  /**
   * Append text to a stream output.
   */
  appendStreamOutput(index: number, text: string, origin: any = null): void {
    this.transact(
      () => {
        const output = this._youtputs.get(index);
        const prevText = output.get('text') as Y.Text;
        prevText.insert(prevText.length, text);
      },
      false,
      origin
    );
  }

  /**
   * Replace content from `start' to `end` with `outputs`.
   *
   * @param start: The start index of the range to replace (inclusive).
   *
   * @param end: The end index of the range to replace (exclusive).
   *
   * @param outputs: New outputs (optional).
   */
  updateOutputs(
    start: number,
    end: number,
    outputs: Array<nbformat.IOutput> = [],
    origin: any = null
  ): void {
    const fin =
      end < this._youtputs.length ? end - start : this._youtputs.length - start;
    this.transact(
      () => {
        this._youtputs.delete(start, fin);
        const newOutputs = this.createOutputs(outputs);
        this._youtputs.insert(start, newOutputs);
      },
      false,
      origin
    );
  }

  /**
   * Clear all outputs from the cell.
   */
  clearOutputs(origin: any = null): void {
    this.transact(
      () => {
        this._youtputs.delete(0, this._youtputs.length);
      },
      false,
      origin
    );
  }

  /**
   * Serialize the model to JSON.
   */
  toJSON(): nbformat.ICodeCell {
    return {
      ...(super.toJSON() as nbformat.ICodeCell),
      outputs: this.getOutputs(),
      execution_count: this.execution_count
    };
  }

  /**
   * Extract changes from YJS events
   *
   * @param events YJS events
   * @returns Cell changes
   */
  protected getChanges(events: Y.YEvent<any>[]): Partial<CellChange> {
    const changes = super.getChanges(events);

    const streamOutputEvent = events.find(
      // Changes to the 'text' of a cell's stream output can be accessed like so:
      // ycell['outputs'][output_idx]['text']
      // This translates to an event path of: ['outputs', output_idx, 'text]
      event =>
        event.path.length === 3 &&
        event.path[0] === 'outputs' &&
        event.path[2] === 'text'
    );
    if (streamOutputEvent) {
      changes.streamOutputChange = streamOutputEvent.changes.delta as any;
    }

    const outputEvent = events.find(
      event => event.target === this.ymodel.get('outputs')
    );
    if (outputEvent) {
      changes.outputsChange = outputEvent.changes.delta as any;
    }

    const modelEvent = events.find(event => event.target === this.ymodel) as
      | undefined
      | Y.YMapEvent<any>;

    if (modelEvent && modelEvent.keysChanged.has('execution_count')) {
      const change = modelEvent.changes.keys.get('execution_count');
      changes.executionCountChange = {
        oldValue: change!.oldValue,
        newValue: this.ymodel.get('execution_count')
      };
    }

    if (modelEvent && modelEvent.keysChanged.has('execution_state')) {
      const change = modelEvent.changes.keys.get('execution_state');
      changes.executionStateChange = {
        oldValue: change!.oldValue,
        newValue: this.ymodel.get('execution_state')
      };
    }

    return changes;
  }

  private _youtputs: Y.Array<Y.Map<any>>;
}

class YAttachmentCell
  extends YBaseCell<nbformat.IBaseCellMetadata>
  implements ISharedAttachmentsCell
{
  /**
   * Cell attachments
   */
  get attachments(): nbformat.IAttachments | undefined {
    return this.getAttachments();
  }
  set attachments(v: nbformat.IAttachments | undefined) {
    this.setAttachments(v);
  }

  /**
   * Gets the cell attachments.
   *
   * @returns The cell attachments.
   */
  getAttachments(): nbformat.IAttachments | undefined {
    return this.ymodel.get('attachments');
  }

  /**
   * Sets the cell attachments
   *
   * @param attachments: The cell attachments.
   */
  setAttachments(attachments: nbformat.IAttachments | undefined): void {
    this.transact(() => {
      if (attachments == null) {
        this.ymodel.delete('attachments');
      } else {
        this.ymodel.set('attachments', attachments);
      }
    }, false);
  }

  /**
   * Extract changes from YJS events
   *
   * @param events YJS events
   * @returns Cell changes
   */
  protected getChanges(events: Y.YEvent<any>[]): Partial<CellChange> {
    const changes = super.getChanges(events);

    const modelEvent = events.find(event => event.target === this.ymodel) as
      | undefined
      | Y.YMapEvent<any>;

    if (modelEvent && modelEvent.keysChanged.has('attachments')) {
      const change = modelEvent.changes.keys.get('attachments');
      changes.attachmentsChange = {
        oldValue: change!.oldValue,
        newValue: this.ymodel.get('attachments')
      };
    }

    return changes;
  }
}

/**
 * Shareable raw cell.
 */
export class YRawCell extends YAttachmentCell implements ISharedRawCell {
  /**
   * Create a new YRawCell that works standalone. It cannot be
   * inserted into a YNotebook because the Yjs model is already
   * attached to an anonymous Y.Doc instance.
   */
  static create(id?: string): YRawCell {
    return super.create(id) as YRawCell;
  }

  /**
   * String identifying the type of cell.
   */
  get cell_type(): 'raw' {
    return 'raw';
  }

  /**
   * Serialize the model to JSON.
   */
  toJSON(): nbformat.IRawCell {
    return {
      id: this.getId(),
      cell_type: 'raw',
      source: this.getSource(),
      metadata: this.getMetadata(),
      attachments: this.getAttachments()
    };
  }
}

/**
 * Shareable markdown cell.
 */
export class YMarkdownCell
  extends YAttachmentCell
  implements ISharedMarkdownCell
{
  /**
   * Create a new YMarkdownCell that works standalone. It cannot be
   * inserted into a YNotebook because the Yjs model is already
   * attached to an anonymous Y.Doc instance.
   */
  static create(id?: string): YMarkdownCell {
    return super.create(id) as YMarkdownCell;
  }

  /**
   * String identifying the type of cell.
   */
  get cell_type(): 'markdown' {
    return 'markdown';
  }

  /**
   * Serialize the model to JSON.
   */
  toJSON(): nbformat.IMarkdownCell {
    return {
      id: this.getId(),
      cell_type: 'markdown',
      source: this.getSource(),
      metadata: this.getMetadata(),
      attachments: this.getAttachments()
    };
  }
}
