/* -----------------------------------------------------------------------------
| Copyright (c) Jupyter Development Team.
| Distributed under the terms of the Modified BSD License.
|----------------------------------------------------------------------------*/

import { Awareness } from 'y-protocols/awareness';
import * as Y from 'yjs';
import type { ISharedText } from './api.js';

/**
 * Abstract interface to define Shared Models that can be bound to a text editor using any existing
 * Yjs-based editor binding.
 */
export interface IYText extends ISharedText {
  /**
   * Shareable text
   */
  readonly ysource: Y.Text;
  /**
   * Shareable awareness
   */
  readonly awareness: Awareness | null;
  /**
   * Undo manager
   */
  readonly undoManager: Y.UndoManager | null;
}
