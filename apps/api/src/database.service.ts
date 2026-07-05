import { Injectable, OnModuleDestroy } from '@nestjs/common';
import { PrismaClient } from '@sprp/database';

@Injectable()
export class DatabaseService extends PrismaClient implements OnModuleDestroy {
  async onModuleDestroy(): Promise<void> { await this.$disconnect(); }
}
