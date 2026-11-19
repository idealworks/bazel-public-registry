#ifndef GPGME_CONFIG_H
#define GPGME_CONFIG_H

#define PACKAGE "gpgme"
#define PACKAGE_NAME "gpgme"
#define PACKAGE_VERSION "2.0.1"
#define VERSION "2.0.1"

#define BUILD_REVISION "53c8f291"
#define BUILD_COMMITID "53c8f29125ff9664120879b78fb11a6e766f89f4"
#define BUILD_TIMESTAMP "<none>"

#define HAVE_CONFIG_H 1
#define HAVE_STDINT_H 1
#define HAVE_INTTYPES_H 1
#define HAVE_SYS_TYPES_H 1
#define HAVE_SYS_STAT_H 1
#define HAVE_UNISTD_H 1
#define HAVE_LOCALE_H 1
#define HAVE_SYS_TIME_H 1
#define HAVE_SYS_SELECT_H 1
#define HAVE_SYS_UIO_H 1
#define HAVE_FCNTL_H 1
#define HAVE_POLL_H 1

#define HAVE_FSEEKO 1
#define HAVE_STPCPY 1
#define HAVE_TIMEGM 1
#define HAVE_SETLOCALE 1
#define HAVE_GETENV 1
#define HAVE_NANOSLEEP 1
#define HAVE_GETGID 1
#define HAVE_GETEGID 1
#define HAVE_CLOSEFROM 1

#define _GNU_SOURCE 1
#define _REENTRANT 1

#define USE_DESCRIPTOR_PASSING 1
#define ENABLE_UISERVER 1
#define USE_LINUX_GETDENTS 1

#define SIZEOF_UNSIGNED_INT 4
#define SIZEOF_UNSIGNED_LONG 8
#define SIZEOF_VOID_P 8

#define GPG_ERR_SOURCE_DEFAULT GPG_ERR_SOURCE_GPGME

#define GPGRT_ENABLE_ES_MACROS 1
#define GPGRT_ENABLE_LOG_MACROS 1
#define GPGRT_ENABLE_ARGPARSE_MACROS 1

#if __GNUC__ > 2
# define GPGME_GCC_A_PURE  __attribute__ ((__pure__))
#else
# define GPGME_GCC_A_PURE
#endif

#ifdef HAVE_DOSISH_SYSTEM
# define PATHSEP_C ';'
# define DIRSEP_C '\\'
# define DIRSEP_S "\\"
#else
# define PATHSEP_C ':'
# define DIRSEP_C '/'
# define DIRSEP_S "/"
#endif

#define GPG_ERR_ENABLE_GETTEXT_MACROS 1

#define FLEXIBLE_ARRAY_MEMBER

#define HAVE_TLS 1

#define HAVE_TLS 1

#define CRIGHTBLURB "Copyright (C) 2000 Werner Koch\n" \
                    "Copyright (C) 2001--2025 g10 Code GmbH\n"

#endif /* GPGME_CONFIG_H */
