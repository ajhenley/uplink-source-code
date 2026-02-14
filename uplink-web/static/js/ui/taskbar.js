/**
 * Running tasks display with progress bars.
 * Shows active hacking tools with their progress and allows cancellation.
 */
const TaskBar = {
    container: null,

    init() {
        this.container = document.getElementById('task-bar');
        GameState.on('tasks_updated', () => this.render());
    },

    /**
     * Render the list of active tasks with progress bars.
     */
    render() {
        if (!this.container) return;
        const tasks = (GameState.tasks || []).filter(t => t.is_active);

        if (tasks.length === 0) {
            this.container.innerHTML = '';
            return;
        }

        this.container.innerHTML = tasks.map(t => {
            const targetStr = t.target_ip ? ' \u2192 ' + t.target_ip : '';
            const progressPct = ((t.progress || 0) * 100).toFixed(1);
            return '<div class="task-item">'
                + '<div class="task-header">'
                + '<span class="task-name">' + this.esc(t.tool_name) + targetStr + '</span>'
                + '<span class="task-cancel" onclick="TaskBar.cancel(' + t.id + ')">[ STOP ]</span>'
                + '</div>'
                + '<div class="task-progress">'
                + '<div class="task-progress-fill" style="width:' + progressPct + '%"></div>'
                + '</div>'
                + '</div>';
        }).join('');
    },

    /**
     * Cancel a running task by ID.
     * @param {number} taskId
     */
    cancel(taskId) {
        GameSocket.stopTool(taskId);
    },

    /**
     * Escape HTML to prevent XSS.
     * @param {string} str
     * @returns {string}
     */
    esc(str) {
        const d = document.createElement('div');
        d.textContent = str || '';
        return d.innerHTML;
    }
};
