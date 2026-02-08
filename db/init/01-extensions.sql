-- Install extensions on databases that need them

-- chatcraft_auth needs uuid-ossp
\c chatcraft_auth
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- chatcraft_org needs uuid-ossp
\c chatcraft_org
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- chatcraft_doc needs uuid-ossp and pgvector
\c chatcraft_doc
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "vector";

-- chatcraft_workspace needs uuid-ossp
\c chatcraft_workspace
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- chatcraft_billing needs uuid-ossp
\c chatcraft_billing
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- chatcraft_notification needs uuid-ossp
\c chatcraft_notification
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
