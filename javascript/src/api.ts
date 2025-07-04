/* -----------------------------------------------------------------------------
| Copyright (c) Jupyter Development Team.
| Distributed under the terms of the Modified BSD License.
|----------------------------------------------------------------------------*/

/**
 * This file defines the shared shared-models types.
 *
 * - Notebook Type.
 * - Notebook Metadata Types.
 * - Cell Types.
 * - Cell Metadata Types.
 *
 * It also defines the shared changes to be used in the events.
 */

import type * as nbformat from '@jupyterlab/nbformat';
import type {
  JSONObject,
  JSONValue,
  PartialJSONValue
} from '@lumino/coreutils';
import type { IObservableDisposable } from '@lumino/disposable';
import type { ISignal } from '@lumino/signaling';
import * as Y from 'yjs';
import { IAwareness } from './awareness.js';

/**
 * Changes on Sequence-like data are expressed as Quill-inspired deltas.
 *
 * @source https://quilljs.com/docs/delta/
 */
export type Delta<T> = Array<{ insert?: T; delete?: number; retain?: number }>;

/**
 * Changes on a map-like data.
 */
export type MapChanges = Map<
  string,
  {
    action: 'add' | 'update' | 'delete';
    oldValue: any;
  }
>;

/**
 * ISharedBase defines common operations that can be performed on any shared object.
 */
export interface ISharedBase extends IObservableDisposable {
  /**
   * Undo an operation.
   */
  undo(): void;

  /**
   * Redo an operation.
   */
  redo(): void;

  /**
   * Whether the object can redo changes.
   */
  canUndo(): boolean;

  /**
   * Whether the object can undo changes.
   */
  canRedo(): boolean;

  /**
   * Clear the change stack.
   */
  clearUndoHistory(): void;

  /**
   * Perform a transaction. While the function f is called, all changes to the shared
   * document are bundled into a single event.
   *
   * @param f Transaction to execute
   * @param undoable Whether to track the change in the action history or not (default `true`)
   */
  transact(f: () => void, undoable?: boolean, origin?: any): void;
}

/**
 * Implement an API for Context information on the shared information.
 * This is used by, for example, docregistry to share the file-path of the edited content.
 */
interface ISharedDocumentNoSource extends ISharedBase {
  /**
   * Document version
   */
  readonly version: string;

  /**
   * Document state
   */
  readonly state: JSONObject;

  /**
   * Document awareness
   */
  readonly awareness: IAwareness;

  /**
   * Get the value for a state attribute
   *
   * @param key Key to get
   */
  getState(key: string): JSONValue | undefined;

  /**
   * Set the value of a state attribute
   *
   * @param key Key to set
   * @param value New attribute value
   */
  setState(key: string, value: JSONValue): void;

  /**
   * The changed signal.
   */
  readonly changed: ISignal<this, DocumentChange>;
}

/**
 * Implement an API for Context information on the shared information.
 * This is used by, for example, docregistry to share the file-path of the edited content.
 */
export interface ISharedDocument extends ISharedDocumentNoSource {
  /**
   * Get the document source.
   *
   * @returns Source.
   */
  getSource(): string | JSONValue;

  /**
   * Set the document source.
   *
   * @param value New source.
   */
  setSource(value: string | JSONValue): void;
}

/**
 * The ISharedText interface defines models that can be bound to a text editor like CodeMirror.
 */
export interface ISharedText extends ISharedBase {
  /**
   * The changed signal.
   */
  readonly changed: ISignal<this, SourceChange>;

  /**
   * Text
   */
  source: string;

  /**
   * Get text.
   *
   * @returns Text.
   */
  getSource(): string;

  /**
   * Set text.
   *
   * @param value New text.
   */
  setSource(value: string): void;

  /**
   * Replace content from `start` to `end` with `value`.
   *
   * @param start: The start index of the range to replace (inclusive).
   * @param end: The end index of the range to replace (exclusive).
   * @param value: New source (optional).
   */
  updateSource(start: number, end: number, value?: string): void;
}

/**
 * Text/Markdown/Code files are represented as ISharedFile
 */
export interface ISharedFile extends ISharedDocumentNoSource, ISharedText {
  /**
   * The changed signal.
   */
  readonly changed: ISignal<this, FileChange>;
}

/**
 * Implements an API for nbformat.INotebookContent
 */
export interface ISharedNotebook extends ISharedDocument {
  /**
   * The changed signal.
   */
  readonly changed: ISignal<this, NotebookChange>;

  /**
   * Signal triggered when a metadata changes.
   */
  readonly metadataChanged: ISignal<this, IMapChange>;

  /**
   * The list of shared cells in the notebook.
   */
  readonly cells: ISharedCell[];

  /**
   * Wether the undo/redo logic should be
   * considered on the full document across all cells.
   */
  readonly disableDocumentWideUndoRedo?: boolean;

  /**
   * Notebook metadata.
   */
  metadata: nbformat.INotebookMetadata;

  /**
   * The minor version number of the nbformat.
   */
  readonly nbformat_minor: number;

  /**
   * The major version number of the nbformat.
   */
  readonly nbformat: number;

  /**
   * Delete a metadata notebook.
   *
   * @param key The key to delete
   */
  deleteMetadata(key: string): void;

  /**
   * Returns all metadata associated with the notebook.
   *
   * @returns Notebook's metadata.
   */
  getMetadata(): nbformat.INotebookMetadata;

  /**
   * Returns a metadata associated with the notebook.
   *
   * @param key Key to get from the metadata
   * @returns Notebook's metadata.
   */
  getMetadata(key: string): PartialJSONValue | undefined;

  /**
   * Sets all metadata associated with the notebook.
   *
   * @param metadata All Notebook's metadata.
   */
  setMetadata(metadata: nbformat.INotebookMetadata): void;

  /**
   * Sets a metadata associated with the notebook.
   *
   * @param metadata The key to set.
   * @param value New metadata value
   */
  setMetadata(metadata: string, value: PartialJSONValue): void;

  /**
   * Updates the metadata associated with the notebook.
   *
   * @param value: Metadata's attribute to update.
   */
  updateMetadata(value: Partial<nbformat.INotebookMetadata>): void;

  /**
   * Add a shared cell at the notebook bottom.
   *
   * @param cell Cell to add.
   *
   * @returns The added cell.
   */
  addCell(cell: SharedCell.Cell): ISharedCell;

  /**
   * Get a shared cell by index.
   *
   * @param index: Cell's position.
   *
   * @returns The requested shared cell.
   */
  getCell(index: number): ISharedCell;

  /**
   * Insert a shared cell into a specific position.
   *
   * @param index Cell's position.
   * @param cell Cell to insert.
   *
   * @returns The inserted cell.
   */
  insertCell(index: number, cell: SharedCell.Cell): ISharedCell;

  /**
   * Insert a list of shared cells into a specific position.
   *
   * @param index Position to insert the cells.
   * @param cells Array of shared cells to insert.
   *
   * @returns The inserted cells.
   */
  insertCells(index: number, cells: Array<SharedCell.Cell>): ISharedCell[];

  /**
   * Move a cell.
   *
   * @param fromIndex: Index of the cell to move.
   * @param toIndex: New position of the cell.
   */
  moveCell(fromIndex: number, toIndex: number): void;

  /**
   * Move cells.
   *
   * @param fromIndex: Index of the first cells to move.
   * @param toIndex: New position of the first cell (in the current array).
   * @param n: Number of cells to move (default 1)
   */
  moveCells(fromIndex: number, toIndex: number, n?: number): void;

  /**
   * Remove a cell.
   *
   * @param index: Index of the cell to remove.
   */
  deleteCell(index: number): void;

  /**
   * Remove a range of cells.
   *
   * @param from: The start index of the range to remove (inclusive).
   *
   * @param to: The end index of the range to remove (exclusive).
   */
  deleteCellRange(from: number, to: number): void;

  /**
   * Override the notebook with a JSON-serialized document.
   *
   * @param value The notebook
   */
  fromJSON(value: nbformat.INotebookContent): void;

  /**
   * Serialize the model to JSON.
   */
  toJSON(): nbformat.INotebookContent;
}

/**
 * Definition of the map changes for yjs.
 */
export type MapChange = Map<
  string,
  { action: 'add' | 'update' | 'delete'; oldValue: any; newValue: any }
>;

/**
 * The namespace for `ISharedNotebook` class statics.
 */
export namespace ISharedNotebook {
  /**
   * The options used to initialize a a ISharedNotebook
   */
  export interface IOptions {
    /**
     * Wether the the undo/redo logic should be
     * considered on the full document across all cells.
     */
    disableDocumentWideUndoRedo?: boolean;

    /**
     * The content of the notebook.
     */
    data?: Partial<nbformat.INotebookContent>;
  }
}

/** Cell Types. */
export type ISharedCell =
  | ISharedCodeCell
  | ISharedRawCell
  | ISharedMarkdownCell
  | ISharedUnrecognizedCell;

/**
 * Shared cell namespace
 */
export namespace SharedCell {
  /**
   * Cell data
   */
  export type Cell = (
    | Partial<nbformat.IRawCell>
    | Partial<nbformat.ICodeCell>
    | Partial<nbformat.IMarkdownCell>
    | Partial<nbformat.IBaseCell>
  ) & { cell_type: string };

  /**
   * Shared cell constructor options.
   */
  export interface IOptions {
    /**
     * Optional notebook to which this cell belongs.
     *
     * If not provided the cell will be standalone.
     */
    notebook?: ISharedNotebook;
  }
}

/**
 * Implements an API for nbformat.IBaseCell.
 */
export interface ISharedBaseCell<
  Metadata extends nbformat.IBaseCellMetadata = nbformat.IBaseCellMetadata
> extends ISharedText {
  /**
   * The type of the cell.
   */
  readonly cell_type: nbformat.CellType | string;

  /**
   * The changed signal.
   */
  readonly changed: ISignal<this, CellChange>;

  /**
   * Cell id.
   */
  readonly id: string;

  /**
   * Whether the cell is standalone or not.
   *
   * If the cell is standalone. It cannot be
   * inserted into a YNotebook because the Yjs model is already
   * attached to an anonymous Y.Doc instance.
   */
  readonly isStandalone: boolean;

  /**
   * Cell metadata.
   *
   * #### Notes
   * You should prefer to access and modify the specific key of interest.
   */
  metadata: Partial<Metadata>;

  /**
   * Signal triggered when the cell metadata changes.
   */
  readonly metadataChanged: ISignal<this, IMapChange>;

  /**
   * The notebook that this cell belongs to.
   */
  readonly notebook: ISharedNotebook | null;

  /**
   * Get Cell id.
   *
   * @returns Cell id.
   */
  getId(): string;

  /**
   * Delete a metadata cell.
   *
   * @param key The key to delete
   */
  deleteMetadata(key: string): void;

  /**
   * Returns all metadata associated with the cell.
   *
   * @returns Cell's metadata.
   */
  getMetadata(): Partial<Metadata>;

  /**
   * Returns a metadata associated with the cell.
   *
   * @param key Metadata key to get
   * @returns Cell's metadata.
   */
  getMetadata(key: string): PartialJSONValue | undefined;

  /**
   * Sets some cell metadata.
   *
   * @param metadata Cell's metadata.
   */
  setMetadata(metadata: Partial<Metadata>): void;

  /**
   * Sets a cell metadata.
   *
   * @param metadata Cell's metadata key.
   * @param value Metadata value
   */
  setMetadata(metadata: string, value: PartialJSONValue): void;

  /**
   * Serialize the model to JSON.
   */
  toJSON(): nbformat.IBaseCell;
}

export type IExecutionState = 'running' | 'idle';

/**
 * Implements an API for nbformat.ICodeCell.
 */
export interface ISharedCodeCell
  extends ISharedBaseCell<nbformat.IBaseCellMetadata> {
  /**
   * The type of the cell.
   */
  cell_type: 'code';

  /**
   * The code cell's prompt number. Will be null if the cell has not been run.
   */
  execution_count: nbformat.ExecutionCount;

  /**
   * The code cell's execution state.
   */
  executionState: IExecutionState;

  /**
   * Cell outputs
   */
  outputs: Array<nbformat.IOutput>;

  /**
   * Execution, display, or stream outputs.
   */
  getOutputs(): Array<nbformat.IOutput>;

  /**
   * Add/Update output.
   */
  setOutputs(outputs: Array<nbformat.IOutput>): void;

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
    outputs: Array<nbformat.IOutput>
  ): void;

  /**
   * Clear all outputs from the cell.
   */
  clearOutputs(origin: any): void;

  /**
   * Serialize the model to JSON.
   */
  toJSON(): nbformat.IBaseCell;
}

/**
 * Cell with attachment interface.
 */
export interface ISharedAttachmentsCell
  extends ISharedBaseCell<nbformat.IBaseCellMetadata> {
  /**
   * Cell attachments
   */
  attachments?: nbformat.IAttachments;

  /**
   * Gets the cell attachments.
   *
   * @returns The cell attachments.
   */
  getAttachments(): nbformat.IAttachments | undefined;

  /**
   * Sets the cell attachments
   *
   * @param attachments: The cell attachments.
   */
  setAttachments(attachments: nbformat.IAttachments | undefined): void;
}

/**
 * Implements an API for nbformat.IMarkdownCell.
 */
export interface ISharedMarkdownCell extends ISharedAttachmentsCell {
  /**
   * String identifying the type of cell.
   */
  cell_type: 'markdown';

  /**
   * Serialize the model to JSON.
   */
  toJSON(): nbformat.IMarkdownCell;
}

/**
 * Implements an API for nbformat.IRawCell.
 */
export interface ISharedRawCell extends ISharedAttachmentsCell {
  /**
   * String identifying the type of cell.
   */
  cell_type: 'raw';

  /**
   * Serialize the model to JSON.
   */
  toJSON(): nbformat.IRawCell;
}

/**
 * Implements an API for nbformat.IUnrecognizedCell.
 */
export interface ISharedUnrecognizedCell
  extends ISharedBaseCell<nbformat.IBaseCellMetadata> {
  /**
   * The type of the cell.
   *
   * The notebook format specified the type will not be 'markdown' | 'raw' | 'code'
   */
  cell_type: string;

  /**
   * Serialize the model to JSON.
   */
  toJSON(): nbformat.IUnrecognizedCell;
}

export type StateChange<T> = {
  /**
   * Key changed
   */
  name: string;
  /**
   * Old value
   */
  oldValue?: T;
  /**
   * New value
   */
  newValue?: T;
};

/**
 * Generic document change
 */
export type DocumentChange = {
  /**
   * Change occurring in the document state.
   */
  stateChange?: StateChange<any>[];
};

/**
 * The change types which occur on an observable map.
 */
export type MapChangeType =
  /**
   * An entry was added.
   */
  | 'add'

  /**
   * An entry was removed.
   */
  | 'remove'

  /**
   * An entry was changed.
   */
  | 'change';

/**
 * The changed args object which is emitted by an observable map.
 */
export interface IMapChange<T = any> {
  /**
   * The type of change undergone by the map.
   */
  type: MapChangeType;

  /**
   * The key of the change.
   */
  key: string;

  /**
   * The old value of the change.
   */
  oldValue?: T;

  /**
   * The new value of the change.
   */
  newValue?: T;
}

/**
 * Text source change
 */
export type SourceChange = {
  /**
   * Text source change
   */
  sourceChange?: Delta<string>;
};

/**
 * Definition of the shared Notebook changes.
 */
export type NotebookChange = DocumentChange & {
  /**
   * Cell changes
   */
  cellsChange?: Delta<ISharedCell[]>;
  /**
   * Notebook metadata changes
   */
  metadataChange?: MapChanges;
  /**
   * nbformat version change
   */
  nbformatChanged?: {
    key: string;
    oldValue?: number;
    newValue?: number;
  };
};

/**
 * File change
 */
export type FileChange = DocumentChange & SourceChange;

/**
 * Definition of the shared Cell changes.
 */
export type CellChange = SourceChange & {
  /**
   * Cell attachment change
   */
  attachmentsChange?: {
    oldValue?: nbformat.IAttachments;
    newValue?: nbformat.IAttachments;
  };
  /**
   * Cell output changes
   */
  outputsChange?: Delta<Y.Map<any>>;
  /**
   * Cell stream output text changes
   */
  streamOutputChange?: Delta<Y.Text>;
  /**
   * Cell execution count change
   */
  executionCountChange?: {
    oldValue?: number;
    newValue?: number;
  };
  /**
   * Cell execution state change
   */
  executionStateChange?: {
    oldValue?: IExecutionState;
    newValue?: IExecutionState;
  };
  /**
   * Cell metadata change
   */
  metadataChange?: MapChanges;
};
