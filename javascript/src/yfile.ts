/* -----------------------------------------------------------------------------
| Copyright (c) Jupyter Development Team.
| Distributed under the terms of the Modified BSD License.
|----------------------------------------------------------------------------*/

import * as Y from 'yjs';
import type { Delta, FileChange, ISharedFile, ISharedText } from './api.js';
import { IYText } from './ytext.js';
import { YDocument } from './ydocument.js';

/**
 * Shareable text file.
 */
export class YFile
  extends YDocument<FileChange>
  implements ISharedFile, ISharedText, IYText
{
  /**
   * Create a new file
   *
   * #### Notes
   * The document is empty and must be populated
   */
  constructor() {
    super();
    this.undoManager.addToScope(this.ysource);
    this.ysource.observe(this._modelObserver);
  }

  /**
   * Document version
   */
  readonly version: string = '1.0.0';

  /**
   * Creates a standalone YFile
   */
  static create(): YFile {
    return new YFile();
  }

  /**
   * YJS file text.
   */
  readonly ysource = this.ydoc.getText('source');

  /**
   * File text
   */
  get source(): string {
    return this.getSource();
  }
  set source(v: string) {
    this.setSource(v);
  }

  /**
   * Dispose of the resources.
   */
  dispose(): void {
    if (this.isDisposed) {
      return;
    }
    this.ysource.unobserve(this._modelObserver);
    super.dispose();
  }

  /**
   * Get the file text.
   *
   * @returns File text.
   */
  getSource(): string {
    return this.ysource.toString();
  }

  /**
   * Set the file text.
   *
   * @param value New text
   */
  setSource(value: string): void {
    this.transact(() => {
      const ytext = this.ysource;
      ytext.delete(0, ytext.length);
      ytext.insert(0, value);
    });
  }

  /**
   * Replace content from `start' to `end` with `value`.
   *
   * @param start: The start index of the range to replace (inclusive).
   * @param end: The end index of the range to replace (exclusive).
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
   * Handle a change to the ymodel.
   */
  private _modelObserver = (event: Y.YTextEvent) => {
    this._changed.emit({ sourceChange: event.changes.delta as Delta<string> });
  };
}
