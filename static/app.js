const state = {
  filter: "all",
  tasks: [],
  loading: true,
  busyIds: new Set(),
};

const elements = {
  taskForm: document.getElementById("taskForm"),
  titleInput: document.getElementById("title"),
  submitButton: document.getElementById("submitButton"),
  formError: document.getElementById("formError"),
  loadingState: document.getElementById("loadingState"),
  emptyState: document.getElementById("emptyState"),
  taskList: document.getElementById("taskList"),
  statusBanner: document.getElementById("statusBanner"),
  totalCount: document.getElementById("totalCount"),
  completedCount: document.getElementById("completedCount"),
  pendingCount: document.getElementById("pendingCount"),
  taskTemplate: document.getElementById("taskTemplate"),
  filterButtons: [...document.querySelectorAll(".filter-button")],
};

async function api(path, options = {}) {
  const response = await fetch(path, {
    headers: {
      "Content-Type": "application/json",
    },
    ...options,
  });

  const data = await response.json().catch(() => ({}));
  if (!response.ok) {
    throw new Error(data.error || "Something went wrong.");
  }
  return data;
}

function setBanner(message = "", isError = false) {
  if (!message) {
    elements.statusBanner.hidden = true;
    elements.statusBanner.textContent = "";
    elements.statusBanner.classList.remove("error");
    return;
  }

  elements.statusBanner.hidden = false;
  elements.statusBanner.textContent = message;
  elements.statusBanner.classList.toggle("error", isError);
}

function setFormError(message = "") {
  elements.formError.hidden = !message;
  elements.formError.textContent = message;
}

function setLoading(loading) {
  state.loading = loading;
  elements.loadingState.hidden = !loading;
}

function updateSummary(tasks) {
  const completed = tasks.filter((task) => task.completed).length;
  const pending = tasks.length - completed;
  elements.totalCount.textContent = String(tasks.length);
  elements.completedCount.textContent = String(completed);
  elements.pendingCount.textContent = String(pending);
}

function renderTasks(tasks) {
  updateSummary(tasks);
  elements.taskList.innerHTML = "";

  if (!tasks.length) {
    elements.taskList.hidden = true;
    elements.emptyState.hidden = false;
    return;
  }

  elements.emptyState.hidden = true;
  elements.taskList.hidden = false;

  tasks.forEach((task) => {
    const fragment = elements.taskTemplate.content.cloneNode(true);
    const card = fragment.querySelector(".task-card");
    const title = fragment.querySelector(".task-title");
    const badge = fragment.querySelector(".task-badge");
    const meta = fragment.querySelector(".task-meta");
    const checkbox = fragment.querySelector(".toggle-task");
    const editButton = fragment.querySelector(".edit-button");
    const deleteButton = fragment.querySelector(".delete-button");

    card.classList.add(task.completed ? "completed" : "pending");
    title.textContent = task.title;
    badge.textContent = task.completed ? "Completed" : "Pending";
    meta.textContent = `Created ${new Date(task.createdAt).toLocaleString()}`;
    checkbox.checked = task.completed;
    checkbox.disabled = state.busyIds.has(task.id);
    editButton.disabled = state.busyIds.has(task.id);
    deleteButton.disabled = state.busyIds.has(task.id);

    checkbox.addEventListener("change", async () => {
      await updateTask(task.id, { completed: checkbox.checked }, "Task status updated.");
    });

    editButton.addEventListener("click", () => {
      if (editButton.classList.contains("save-mode")) {
        const input = card.querySelector(".inline-edit");
        saveTitle(task.id, input.value);
        return;
      }

      const input = document.createElement("input");
      input.type = "text";
      input.value = task.title;
      input.className = "inline-edit";
      input.maxLength = 120;
      title.replaceWith(input);
      editButton.textContent = "Save";
      editButton.classList.add("save-mode");
      input.focus();
      input.select();
    });

    deleteButton.addEventListener("click", async () => {
      await deleteTask(task.id);
    });

    elements.taskList.appendChild(fragment);
  });
}

async function loadTasks(showLoader = true) {
  if (showLoader) {
    setLoading(true);
  }
  setBanner();

  try {
    const query = state.filter === "all" ? "" : `?status=${state.filter}`;
    const data = await api(`/tasks${query}`);
    state.tasks = data.tasks;
    renderTasks(state.tasks);
  } catch (error) {
    elements.taskList.hidden = true;
    elements.emptyState.hidden = true;
    setBanner(error.message, true);
  } finally {
    setLoading(false);
  }
}

async function createTask(event) {
  event.preventDefault();
  setFormError();

  const title = elements.titleInput.value.trim();
  if (!title) {
    setFormError("Please enter a task title.");
    return;
  }

  elements.submitButton.disabled = true;
  elements.submitButton.textContent = "Adding...";

  try {
    await api("/tasks", {
      method: "POST",
      body: JSON.stringify({ title }),
    });
    elements.taskForm.reset();
    setBanner("Task created successfully.");
    await loadTasks(false);
  } catch (error) {
    setFormError(error.message);
  } finally {
    elements.submitButton.disabled = false;
    elements.submitButton.textContent = "Add Task";
  }
}

async function updateTask(id, payload, successMessage) {
  state.busyIds.add(id);
  renderTasks(state.tasks);

  try {
    await api(`/tasks/${id}`, {
      method: "PATCH",
      body: JSON.stringify(payload),
    });
    setBanner(successMessage);
    await loadTasks(false);
  } catch (error) {
    setBanner(error.message, true);
    await loadTasks(false);
  } finally {
    state.busyIds.delete(id);
  }
}

async function saveTitle(id, title) {
  const cleanTitle = title.trim();
  if (!cleanTitle) {
    setBanner("Task title cannot be empty.", true);
    await loadTasks(false);
    return;
  }

  await updateTask(id, { title: cleanTitle }, "Task title updated.");
}

async function deleteTask(id) {
  state.busyIds.add(id);
  renderTasks(state.tasks);

  try {
    await api(`/tasks/${id}`, { method: "DELETE" });
    setBanner("Task deleted.");
    await loadTasks(false);
  } catch (error) {
    setBanner(error.message, true);
    await loadTasks(false);
  } finally {
    state.busyIds.delete(id);
  }
}

elements.taskForm.addEventListener("submit", createTask);
elements.filterButtons.forEach((button) => {
  button.addEventListener("click", async () => {
    elements.filterButtons.forEach((item) => item.classList.remove("active"));
    button.classList.add("active");
    state.filter = button.dataset.filter;
    await loadTasks();
  });
});

loadTasks();
