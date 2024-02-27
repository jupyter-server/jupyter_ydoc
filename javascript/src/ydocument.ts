/* -----------------------------------------------------------------------------
| Copyright (c) Jupyter Development Team.
| Distributed under the terms of the Modified BSD License.
|----------------------------------------------------------------------------*/

import { JSONExt, JSONObject, JSONValue } from '@lumino/coreutils';
import { ISignal, Signal } from '@lumino/signaling';
import { Awareness } from 'y-protocols/awareness';
import * as Y from 'yjs';
import type { DocumentChange, IDocumentProvider, ISharedDocument, StateChange } from './api';

/**
 * Generic shareable document.
 */
export abstract class YDocument<T extends DocumentChange>
  implements ISharedDocument
{
  constructor(options?: YDocument.IOptions) {
    this._ydoc = options?.ydoc ?? new Y.Doc();
    this.forkId = options?.forkId ?? 'root';

    this._ystate = this._ydoc.getMap('state');

    this._undoManager = new Y.UndoManager([], {
      trackedOrigins: new Set([this]),
      doc: this._ydoc
    });

    this._awareness = new Awareness(this._ydoc);

    this._ystate.observe(this.onStateChanged);

    this._providers = {};
  }

  /**
   * Document version
   */
  abstract readonly version: string;

  addFork(forkId: string) {
    this.ystate.set(`fork_${forkId}`, 'new');
  }

  getProvider(providerId: string, sharedModel?: ISharedDocument): IDocumentProvider {
    if (!(providerId in this._providers)) {
      if (providerId === 'root') {
        throw new Error('Cannot get a new provider for root document');
      }
      if (sharedModel === undefined) {
        throw new Error('New provider needs a shared document');
      }
      const root_provider = this._providers['root'];
      this._providers[providerId] = root_provider.connectFork(providerId, sharedModel!);
    }
    return this._providers[providerId];
  }

  setProvider(providerId: string, provider: IDocumentProvider) {
    this._providers[providerId] = provider;
  }

  /**
   * YJS document.
   */
  get ydoc(): Y.Doc {
    return this._ydoc;
  }

  /**
   * Shared state
   */
  get ystate(): Y.Map<any> {
    return this._ystate;
  }

  /**
   * YJS document undo manager
   */
  get undoManager(): Y.UndoManager {
    return this._undoManager;
  }

  /**
   * Shared awareness
   */
  get awareness(): Awareness {
    return this._awareness;
  }

  /**
   * The changed signal.
   */
  get changed(): ISignal<this, T> {
    return this._changed;
  }

  /**
   * A signal emitted when the document is disposed.
   */
  get disposed(): ISignal<this, void> {
    return this._disposed;
  }

  /**
   * Whether the document is disposed or not.
   */
  get isDisposed(): boolean {
    return this._isDisposed;
  }

  /**
   * Document state
   */
  get state(): JSONObject {
    return JSONExt.deepCopy(this.ystate.toJSON());
  }

  /**
   * Whether the object can undo changes.
   */
  canUndo(): boolean {
    return this.undoManager.undoStack.length > 0;
  }

  /**
   * Whether the object can redo changes.
   */
  canRedo(): boolean {
    return this.undoManager.redoStack.length > 0;
  }

  /**
   * Dispose of the resources.
   */
  dispose(): void {
    if (this._isDisposed) {
      return;
    }
    this._isDisposed = true;
    this.ystate.unobserve(this.onStateChanged);
    this.awareness.destroy();
    this.undoManager.destroy();
    this.ydoc.destroy();
    this._disposed.emit();
    Signal.clearData(this);
  }

  /**
   * Get the value for a state attribute
   *
   * @param key Key to get
   */
  getState(key: string): JSONValue | undefined {
    const value = this.ystate.get(key);
    return typeof value === 'undefined'
      ? value
      : (JSONExt.deepCopy(value) as unknown as JSONValue);
  }

  /**
   * Set the value of a state attribute
   *
   * @param key Key to set
   * @param value New attribute value
   */
  setState(key: string, value: JSONValue): void {
    if (!JSONExt.deepEqual(this.ystate.get(key), value)) {
      this.ystate.set(key, value);
    }
  }

  /**
   * Undo an operation.
   */
  undo(): void {
    this.undoManager.undo();
  }

  /**
   * Redo an operation.
   */
  redo(): void {
    this.undoManager.redo();
  }

  /**
   * Clear the change stack.
   */
  clearUndoHistory(): void {
    this.undoManager.clear();
  }

  /**
   * Perform a transaction. While the function f is called, all changes to the shared
   * document are bundled into a single event.
   */
  transact(f: () => void, undoable = true): void {
    this.ydoc.transact(f, undoable ? this : null);
  }

  /**
   * Handle a change to the ystate.
   */
  protected onStateChanged = (event: Y.YMapEvent<any>): void => {
    const stateChange = new Array<StateChange<any>>();
    event.keysChanged.forEach(key => {
      const change = event.changes.keys.get(key);
      if (change) {
        stateChange.push({
          name: key,
          oldValue: change.oldValue,
          newValue: this.ystate.get(key)
        });
      }
    });

    this._changed.emit({ stateChange } as any);
  };

  protected _changed = new Signal<this, T>(this);
  private _ydoc: Y.Doc;
  private _ystate: Y.Map<any>;
  private _undoManager: Y.UndoManager;
  private _awareness: Awareness;
  private _isDisposed = false;
  private _disposed = new Signal<this, void>(this);
  private _providers: { [key: string]: IDocumentProvider };
  public forkId: string;
}

/**
 * YDocument namespace
 */
export namespace YDocument {
  /**
   * YDocument constructor options
   */
  export interface IOptions {
    /**
     * The optional YJS document for YDocument.
     */
    ydoc?: Y.Doc;

    /**
     * The document fork ID, defaults to 'root'.
     */
    forkId?: string;
  }
}
