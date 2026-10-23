## Grix 1.1.0 is on the next cycle of updates list

### What kind of updates?

- Reading the state.json from kernel Autotune. This will allow Grix to know two important details, system state and Person profile.
  - What is a Persona profile? Griffin Person is the workflow tool of your system. This tool installs drivers, Wine layers, tools, and more to optimize your desired workflows.
  - What is the state.json? The state.json shows Griffin tools the state of your system. This may vary depending on hardware such as SSD and HDD, but the list includes:
    * script_version
    * last_updated
    * hostname
    * Persona (future feature in the next update cycle)
    * distro
    * distro_id
    * distro_family
    * init_system
    * kernel
    * kernel_version
    * kernel_mm
    * preempt_model
    * device_type
    * gpu_model
    * gpu_driver
    * cpu_model
    * cgroup_version
    * zram_manager
    * power_manager
    * ram_mb
    * cpu_cores
    * has_ssd
    * is_numa
    * has_thermal
    * has_psi
    * is_container
    * config
    * effective
    * cpu_governor
    * thp
    * zram_algo
    * tcp_congestion
    * net_qdisc
    * io_scheduler_ssd
    * io_scheduler_hdd
    * zram_external_policy
    * cpu_tuning_policy
    * swappiness
    * dirty_ratio
    * dirty_bg_ratio
    * dirty_writeback_cs
    * dirty_expire_cs
    * vfs_cache_pressure
    * zram_enabled
    * zram_ratio
    * zswap_enabled
    * numa_balancing
    * compact_unevictable
    * auto_regen
    * cpufreq_driver
    * cpu_epp
    * thp_enabled
    * thp_defrag
    * io_schedulers
    * zswap
    * zram_devices
    * zram_total_mb
    * io_prio_effective

### Why is this imprtant?

- This allows every tool in the Griffin ecosystem to know your system, which makes diagnosing your system with Grix much easier
- You get consistent performance each boot
- Your PC is your own to decide what you want and don't want
- You worry about your work and play, let Griffin worry about keeping it that way
- Grix only observes, Griffin Hub is the tool to manually edit the values of this list
- Fan Hub uses this information for fan curves to give better cooling
- SentryV3 uses this information to better handle slowing down processes
- XKM uses this for kernel management
- Griffin Play (a part of the next update of Griffin Hub) uses this to get better ProtonDB suggestions for Steam launch command fixes
- You don't have to configure anything, unless you want to, then you can in Griffin Hub's system tune settings (which writes to the state.json's config file), completely reversable, completely your settings, or just let it be automated, your choice, your system
- Don't want a tool? Then don't worry, the state.json is only for Griffin, it will not erode how any other performance tools work. Choose one tool, or all of the, your choice, your PC

### How does Grix use this information exactly? Is Grix AI?

- Grix is not AI. Grix is a deterministic companion tool that has AI-like features but has no intelligence like an LLM. Grix is hardcoded with the data it needs to work, there is no, "Let me search Google."
- Let's say you have a system that has multiple Persona profiles set. Your performance is not as great as you'd have hoped. Grix will explain it to you, and explain what settings to choose in Griffin Hub.
- Grix already has part of these features implemented with showing the state.json, but the context aspect still needs to be added
- Outside of that it is responsible for helping you when your Wi-Fi or sound stops working, when your disk space is full it clears unneeded silent storage eaters like a 2-year-old amount of back logs in the journal or cache, snap, flatpak, unused dependencies, and other storage eaters. File permissions, package manager health, and more.

### What are some future updates? 

- Appify aware fixes. With Appify making PWAs behave like real apps without electron, it sometimes can still have its hiccups. Grix will be there when that happens.
- Controller Hub fixes. With third party controllers, some drivers may cause an issue, Grix will understand these issues, and will offer an explanation and fix as it does with everything else
- Better Wayland, Sway, X11, and other display server support and fixes
- Better NVIDIA fixes and support
