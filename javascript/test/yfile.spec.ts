// Copyright (c) Jupyter Development Team.
// Distributed under the terms of the Modified BSD License.

import { Delta, YFile } from '../src';

describe('@jupyter/ydoc', () => {
  describe('YFile', () => {
    describe('#constructor', () => {
      test('should create a document without arguments', () => {
        const file = new YFile();
        expect(file.source.length).toBe(0);
        expect(file.dirty).toBe(false);
        file.dispose();
      });
    });

    describe('#disposed', () => {
      test('should be emitted when the document is disposed', () => {
        const file = new YFile();
        let disposed = false;
        file.disposed.connect(() => {
          disposed = true;
        });
        file.dispose();
        expect(disposed).toEqual(true);
      });
    });

    describe('source', () => {
      test('should set source', () => {
        const file = new YFile();

        const source = 'foo';
        file.source = source;

        expect(file.source).toEqual(source);
        expect(file.dirty).toEqual(false);
        file.dispose();
      });

      test('should get source', () => {
        const file = new YFile();

        const source = 'foo';
        file.source = source;

        expect(file.source).toEqual(source);
        file.dispose();
      });

      test('should update source', () => {
        const file = new YFile();

        const source = 'fooo bar';
        file.source = source;
        expect(file.source).toBe(source);
        expect(file.dirty).toEqual(false);

        file.updateSource(3, 5, '/');
        expect(file.source).toBe('foo/bar');
        expect(file.dirty).toEqual(true);
        file.dispose();
      });

      test('should emit an insert source change', () => {
        const file = new YFile();
        expect(file.source).toBe('');

        const changes: Delta<string>[] = [];
        file.changed.connect((_, c) => {
          changes.push(c.sourceChange!);
        });
        const source = 'foo';
        file.source = source;

        expect(changes).toHaveLength(1);
        expect(changes).toEqual([
          [
            {
              insert: 'foo'
            }
          ]
        ]);

        file.dispose();
      });

      test('should emit a delete source change', () => {
        const file = new YFile();
        const source = 'foo';
        file.source = source;
        expect(file.source).toBe(source);

        const changes: Delta<string>[] = [];
        file.changed.connect((_, c) => {
          changes.push(c.sourceChange!);
        });
        file.source = '';

        expect(changes).toHaveLength(1);
        expect(changes).toEqual([
          [
            {
              delete: 3
            }
          ]
        ]);

        file.dispose();
      });

      test('should emit an update source change', () => {
        const file = new YFile();
        const source1 = 'foo';
        file.source = source1;
        expect(file.source).toBe(source1);

        const changes: Delta<string>[] = [];
        file.changed.connect((_, c) => {
          changes.push(c.sourceChange!);
        });
        const source = 'bar';
        file.source = source;

        expect(changes).toHaveLength(1);
        expect(changes).toEqual([
          [
            {
              delete: 3
            },
            {
              insert: source
            }
          ]
        ]);

        file.dispose();
      });
    });
  });

  describe('#readOnly', () => {
    test('should default to false', () => {
      const file = new YFile();
      expect(file.readOnly).toBe(false);
      file.dispose();
    });

    test('should emit readOnlyChanged when set to true', () => {
      const file = new YFile();
      const changes: boolean[] = [];
      file.readOnlyChanged.connect((_, v) => {
        changes.push(v);
      });
      file.readOnly = true;

      expect(changes).toEqual([true]);
      file.dispose();
    });

    test('should emit readOnlyChanged when toggled back to false', () => {
      const file = new YFile();
      const changes: boolean[] = [];
      file.readOnly = true;
      file.readOnlyChanged.connect((_, v) => {
        changes.push(v);
      });
      file.readOnly = false;

      expect(changes).toEqual([false]);
      file.dispose();
    });

    test('should not emit readOnlyChanged when set to the same value', () => {
      const file = new YFile();
      const changes: boolean[] = [];
      file.readOnlyChanged.connect((_, v) => {
        changes.push(v);
      });
      file.readOnly = false;

      expect(changes).toHaveLength(0);
      file.dispose();
    });

    test('should block source changes when read-only', () => {
      const file = new YFile();
      file.source = 'initial';
      file.readOnly = true;
      file.source = 'blocked';

      expect(file.source).toBe('initial');
      file.dispose();
    });

    test('should block updateSource when read-only', () => {
      const file = new YFile();
      file.source = 'initial';
      file.readOnly = true;
      file.updateSource(0, 0, 'blocked');

      expect(file.source).toBe('initial');
      file.dispose();
    });

    test('canUndo should return false when read-only', () => {
      const file = new YFile();
      file.source = 'hello';
      file.readOnly = true;

      expect(file.canUndo()).toBe(false);
      file.dispose();
    });

    test('undo should return false when read-only', () => {
      const file = new YFile();
      file.source = 'hello';
      file.readOnly = true;

      expect(file.undo()).toBe(false);
      expect(file.source).toBe('hello');
      file.dispose();
    });

    test('canRedo should return false when read-only', () => {
      const file = new YFile();
      file.source = 'hello';
      file.undo();
      file.readOnly = true;

      expect(file.canRedo()).toBe(false);
      file.dispose();
    });

    test('redo should return false when read-only', () => {
      const file = new YFile();
      file.source = 'hello';
      file.undo();
      file.readOnly = true;

      expect(file.redo()).toBe(false);
      expect(file.source).toBe('');
      file.dispose();
    });

    test('should allow changes again after disabling read-only', () => {
      const file = new YFile();
      file.source = 'initial';
      file.readOnly = true;
      file.source = 'blocked';
      file.readOnly = false;
      file.source = 'allowed';

      expect(file.source).toBe('allowed');
      file.dispose();
    });
  });
});
